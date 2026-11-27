"""Avalia a LUT e a CNN no lote de teste: python -m calibracao_branco.holdout_evaluation_cli --help

Roda o mesmo caminho da IHM (TomatoInspectionFacade) em cada foto de Dataset-teste e compara
com os rótulos. A unidade é o tomate; os intervalos de confiança são de Wilson (95%).
Este lote deve ser avaliado uma única vez, depois de os modelos estarem prontos: ajustar algo
olhando para ele tornaria o resultado otimista como o da validação.
"""

import argparse
import csv
import statistics
import sys
from pathlib import Path
from typing import List

import numpy as np

from .binary_metrics import BinaryMetrics
from .defect_classifier import MissingModelDefectClassifierNullObject, defect_classifier_for
from .errors import CalibrationError
from .gain_file import GainFileReader
from .holdout_evaluation import HoldoutEvaluator, HoldoutResult
from .image_files import load_image, save_image
from .inspection_overlay import InspectionOverlay
from .labeled_capture import LabeledPhoto, LabeledPhotoStore
from .maturity_classifier import MissingLutMaturityClassifierNullObject, maturity_classifier_for
from .scale_file import ScaleSectionReader
from .tomato_inspection import InspectionModels, TomatoInspectionFacade
from .wilson_interval import WilsonInterval

MATURITIES = ("imaturo", "intermediario", "maduro")


def main(arguments: List[str] = None) -> int:
    options = _build_parser().parse_args(arguments)
    try:
        _run(options)
    except (CalibrationError, ValueError) as error:
        print(f"ERRO: {error}", file=sys.stderr)
        return 1
    return 0


def _run(options: argparse.Namespace) -> None:
    facade = _build_facade(options)
    dataset_folder = Path(options.pasta)
    output_folder = dataset_folder / "avaliacao"
    photos = LabeledPhotoStore(dataset_folder).labeled_photos()
    if not photos:
        raise CalibrationError(f"Nenhuma foto rotulada em {dataset_folder}.")

    evaluator = HoldoutEvaluator(facade)
    results, failures = [], []
    for photo in photos:
        try:
            results.append(evaluator.evaluate(photo, load_image(photo.path)))
        except CalibrationError as error:
            print(f"AVISO: {error}")
            failures.append(photo)

    _save_images(InspectionOverlay(facade.region), (results, output_folder / "imagens"))
    _save_table(results, output_folder / "por_tomate.csv")
    report = HoldoutReportBuilder(results, failures)
    report.add_defect_section()
    report.add_maturity_section()
    report.add_destination_section()
    report.add_size_and_time_section()
    report.add_per_tomato_table()
    report_file = output_folder / "RELATORIO.md"
    report_file.write_text(report.text(), encoding="utf-8")
    print(report.text())
    print(f"Relatório: {report_file.resolve()}")


def _build_facade(options: argparse.Namespace) -> TomatoInspectionFacade:
    gain_file = Path(options.gain)
    maturity = maturity_classifier_for(Path(options.lut))
    defect = defect_classifier_for(Path(options.cnn))
    if isinstance(maturity, MissingLutMaturityClassifierNullObject):
        raise CalibrationError(f"LUT não encontrada: {options.lut}")
    if isinstance(defect, MissingModelDefectClassifierNullObject):
        raise CalibrationError(f"CNN não encontrada: {options.cnn}")
    return TomatoInspectionFacade(InspectionModels(GainFileReader().read_gains(gain_file),
                                                   ScaleSectionReader().read(gain_file), maturity, defect))


def _save_images(overlay: InspectionOverlay, results_and_folder) -> None:
    results, folder = results_and_folder
    for result in results:
        verdict = "ok" if result.is_destination_correct() else "ERRO"
        name = (f"{verdict}_tomate_{result.photo.tomato_id:04d}_real-{result.expected_destination().title}"
                f"_sistema-{result.inspection.destination().title}.png")
        save_image(overlay.draw(result.report), folder / name)


def _save_table(results: List[HoldoutResult], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["tomate", "maturacao_real", "maturacao_lut", "pct_colorido", "pct_vermelho", "defeito_real",
                         "prob_defeito_cnn", "destino_real", "destino_sistema", "diametro_mm", "comprimento_mm",
                         "largura_mm", "circularidade", "tempo_ms", "objetos_extras"])
        for result in results:
            inspection = result.inspection
            writer.writerow([result.photo.tomato_id, result.photo.maturity, inspection.maturity.label(),
                             _decimal(inspection.maturity.surface.colored_fraction * 100),
                             _decimal(inspection.maturity.surface.red_fraction * 100),
                             int(result.expected_has_defect), _decimal(inspection.defect.defect_probability),
                             result.expected_destination().title, inspection.destination().title,
                             _decimal(inspection.size.diameter_mm), _decimal(inspection.size.length_mm),
                             _decimal(inspection.size.width_mm), _decimal(inspection.size.circularity),
                             _decimal(result.report.elapsed_ms), result.extra_objects])


def _decimal(value: float) -> str:
    return f"{value:.3f}".replace(".", ",")


class HoldoutReportBuilder:
    """Monta o RELATORIO.md do lote de teste por partes (Builder)."""

    def __init__(self, results: List[HoldoutResult], failures: List[LabeledPhoto]):
        self._results, self._failures = results, failures
        self._lines = ["# Avaliação no lote de teste", "",
                       f"Tomates no lote: **{len(results) + len(failures)}** (uma foto por tomate). "
                       f"Não segmentados: {len(failures)}.",
                       "Nenhum destes tomates foi usado no treino da LUT nem da CNN. Intervalos de confiança "
                       "de 95% pelo método de Wilson; com poucos tomates eles são largos, e é isso que o "
                       "resultado permite afirmar.", ""]
        if failures:
            self._lines += ["Fotos sem tomate segmentado (contam como erro no destino): "
                            + ", ".join(photo.path.name for photo in failures), ""]

    def add_defect_section(self) -> None:
        metrics = BinaryMetrics.from_labels(np.array([r.expected_has_defect for r in self._results]),
                                            np.array([r.inspection.defect.has_defect() for r in self._results]))
        healthy, defective = (metrics.true_negatives + metrics.false_positives,
                              metrics.true_positives + metrics.false_negatives)
        self._lines += ["## CNN de defeitos (sadio x com defeito)", "",
                        "| Métrica | Valor |", "|---|---|",
                        f"| Acurácia | {_interval(metrics.true_negatives + metrics.true_positives, metrics.total)} |",
                        f"| Sensibilidade (acha o defeito) | {_interval(metrics.true_positives, defective)} |",
                        f"| Especificidade (passa o sadio) | {_interval(metrics.true_negatives, healthy)} |",
                        f"| Acurácia balanceada | {metrics.balanced_accuracy():.1%} |",
                        f"| Precisão | {metrics.precision():.1%} |", f"| F1 | {metrics.f1():.1%} |", "",
                        "| Real \\ CNN | sadio | com defeito |", "|---|---|---|",
                        f"| sadio | {metrics.true_negatives} | {metrics.false_positives} |",
                        f"| com defeito | {metrics.false_negatives} | {metrics.true_positives} |", ""]

    def add_maturity_section(self) -> None:
        self._lines += ["## LUT de cor (maturação)", "",
                        "Regra: imaturo se < 10% da superfície colorida; maduro se > 60% vermelha; senão "
                        "intermediário. Avaliada em todos os tomates, com ou sem defeito.", "",
                        f"Acerto: {_interval(sum(r.is_maturity_correct() for r in self._results), len(self._results))}",
                        "", "| Real \\ LUT | " + " | ".join(MATURITIES) + " |", "|---|---|---|---|"]
        for real in MATURITIES:
            row = [sum(1 for r in self._results if r.photo.maturity == real and r.inspection.maturity.label() == lut)
                   for lut in MATURITIES]
            self._lines.append(f"| {real} | " + " | ".join(str(count) for count in row) + " |")
        self._lines.append("")

    def add_destination_section(self) -> None:
        correct = sum(r.is_destination_correct() for r in self._results)
        self._lines += ["## Destino final (o que a bancada faria)", "",
                        "Esperado: com defeito -> Descarte; sadio -> classe de maturação do rótulo.", "",
                        f"Acerto: {_interval(correct, len(self._results) + len(self._failures))}", ""]

    def add_size_and_time_section(self) -> None:
        diameters = [r.inspection.size.diameter_mm for r in self._results]
        circularities = [r.inspection.size.circularity for r in self._results]
        # A primeira inspeção inclui a carga do modelo na memória; ela fica fora do tempo típico.
        times = [r.report.elapsed_ms for r in self._results[1:]] or [r.report.elapsed_ms for r in self._results]
        self._lines += ["## Tamanho e tempo", "",
                        "Sem diâmetro de paquímetro nos rótulos, o tamanho não tem referência para erro; "
                        "fica a distribuição medida.", "",
                        "| Medida | Mínimo | Mediana | Máximo |", "|---|---|---|---|",
                        _row("Diâmetro equivalente (mm)", diameters), _row("Circularidade", circularities),
                        _row("Tempo por foto (ms)", times), "",
                        f"Fotos com objetos extras segmentados: {sum(r.extra_objects > 0 for r in self._results)}.",
                        "O tempo é deste computador (inclui balanço de branco, segmentação, LUT e CNN).", ""]

    def add_per_tomato_table(self) -> None:
        self._lines += ["## Por tomate", "",
                        "| Tomate | Maturação real | LUT | % vermelho | Defeito real | P(defeito) | Destino real "
                        "| Destino sistema | Diâmetro (mm) |", "|---|---|---|---|---|---|---|---|---|"]
        for r in self._results:
            mark = "" if r.is_destination_correct() else " ❌"
            self._lines.append(
                f"| {r.photo.tomato_id} | {r.photo.maturity} | {r.inspection.maturity.label()} "
                f"| {r.inspection.maturity.surface.red_fraction:.0%} | {'sim' if r.expected_has_defect else 'não'} "
                f"| {r.inspection.defect.defect_probability:.2f} | {r.expected_destination().title} "
                f"| {r.inspection.destination().title}{mark} | {r.inspection.size.diameter_mm:.1f} |")
        self._lines.append("")

    def text(self) -> str:
        return "\n".join(self._lines) + "\n"


def _interval(successes: int, total: int) -> str:
    return WilsonInterval.for_proportion(successes, total).describe() if total else "sem tomates"


def _row(name: str, values: List[float]) -> str:
    return f"| {name} | {min(values):.2f} | {statistics.median(values):.2f} | {max(values):.2f} |"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m calibracao_branco.holdout_evaluation_cli",
                                     description="Avalia LUT e CNN no lote de teste (tomates nunca vistos).")
    parser.add_argument("--gain", default="bancada.gain", help="Ganhos do branco, região de interesse e escala.")
    parser.add_argument("--pasta", default="../Dataset-teste", help="Pasta com fotos/ e rotulos.csv do teste.")
    parser.add_argument("--lut", default="lut_cor.npz", help="LUT de cor.")
    parser.add_argument("--cnn", default="cnn_defeito.onnx", help="CNN de defeitos.")
    return parser


if __name__ == "__main__":
    sys.exit(main())
