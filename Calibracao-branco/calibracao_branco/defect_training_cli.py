"""Treina a CNN de defeitos: python -m calibracao_branco.defect_training_cli --help

1. Recorta o tomate de cada foto de Dataset-proprio (balanço de branco + segmentação).
2. Validação cruzada por tomate (5 dobras): é ela que estima o desempenho em tomates novos.
3. Modelo final treinado com todos os tomates, pelo número de épocas que as dobras indicaram.
4. Exporta o ONNX, confere que o OpenCV (o caminho da IHM) dá a mesma resposta e escreve o relatório.
"""

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np
import torch

from .binary_metrics import BinaryMetrics
from .defect_classifier import OnnxDefectClassifierAdapter
from .defect_training import (CLASS_NAMES, CropSample, DefectCnnTrainer, EpochRecord, Prediction, TrainingSettings,
                              cross_validation_folds, export_onnx, load_samples)
from .errors import CalibrationError
from .gain_file import GainFileReader
from .image_files import save_image
from .labeled_capture import LabeledPhotoStore
from .tomato_crops import TomatoCropExtractor
from .training_chart import learning_curve_image

ONNX_AGREEMENT_TOLERANCE = 0.02
MINIMUM_FOLDS = 2


@dataclass(frozen=True)
class FoldResult:
    metrics: BinaryMetrics
    best_epoch: int
    predictions: List[Prediction]
    history: List[EpochRecord]


def main(arguments: List[str] = None) -> int:
    options = _build_parser().parse_args(arguments)
    try:
        _run(options)
    except (CalibrationError, ValueError) as error:
        print(f"ERRO: {error}", file=sys.stderr)
        return 1
    return 0


def _run(options: argparse.Namespace) -> None:
    if options.dobras < MINIMUM_FOLDS:
        raise ValueError(f"Use pelo menos {MINIMUM_FOLDS} dobras na validação cruzada.")
    gain_file, dataset_folder = Path(options.gain), Path(options.pasta)
    output_folder = dataset_folder / "cnn"
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Treinando em: {'GPU ' + torch.cuda.get_device_name(0) if device.type == 'cuda' else 'CPU (mais lento)'}")

    extractor = TomatoCropExtractor(GainFileReader().read_gains(gain_file), GainFileReader().read_region(gain_file))
    samples = load_samples(LabeledPhotoStore(dataset_folder), extractor)
    print(_dataset_summary(samples))
    trainer = DefectCnnTrainer(TrainingSettings(epochs=options.epocas), device)

    folds = _cross_validate(trainer, samples, options.dobras)
    _save_fold_outputs(output_folder, folds)
    final_epochs = max(1, int(np.median([fold.best_epoch for fold in folds])))
    print(f"\nModelo final: todos os {len(samples)} recortes, {final_epochs} épocas "
          "(mediana da melhor época das dobras).")
    model = trainer.train_on_all(samples, final_epochs)

    model_file = Path(options.saida)
    export_onnx(model, model_file)
    print(f"Modelo salvo em: {model_file.resolve()}")
    _check_onnx_matches_torch(model_file, trainer.predict(model, samples))

    report = CnnReportBuilder(samples)
    report.add_cross_validation(folds)
    report.add_final_model(final_epochs, options.epocas)
    report_file = output_folder / "RELATORIO.md"
    report_file.write_text(report.text(), encoding="utf-8")
    print(f"\n{report.summary}\nRelatório completo: {report_file.resolve()}")


def _dataset_summary(samples: List[CropSample]) -> str:
    lines = ["Dataset recortado:"]
    for label, name in enumerate(CLASS_NAMES):
        of_class = [s for s in samples if s.label == label]
        lines.append(f"  {name}: {len(of_class)} fotos de {len({s.tomato_id for s in of_class})} tomates")
    return "\n".join(lines)


def _cross_validate(trainer: DefectCnnTrainer, samples: List[CropSample], fold_count: int) -> List[FoldResult]:
    results = []
    for index, (train, validation) in enumerate(cross_validation_folds(samples, fold_count), start=1):
        print(f"\nValidação cruzada - dobra {index} de {fold_count} "
              f"({len({s.tomato_id for s in validation})} tomates de validação)")
        outcome = trainer.train(train, validation)
        predictions = trainer.predict(outcome.model, validation)
        results.append(FoldResult(_metrics_of(predictions), outcome.best_epoch, predictions, outcome.history))
    return results


def _metrics_of(predictions: List[Prediction]) -> BinaryMetrics:
    return BinaryMetrics.from_labels(np.array([p.sample.label for p in predictions]),
                                     np.array([p.predicted_label for p in predictions]))


def _check_onnx_matches_torch(model_file: Path, predictions: List[Prediction]) -> None:
    """O ONNX lido pelo OpenCV tem que dar a mesma resposta do PyTorch; senão a IHM estaria errada."""
    classifier = OnnxDefectClassifierAdapter(model_file)
    worst = max((abs(classifier.classify(p.sample.crop_bgr).defect_probability - p.defect_probability)
                 for p in predictions), default=0.0)
    if worst > ONNX_AGREEMENT_TOLERANCE:
        raise CalibrationError(f"O ONNX no OpenCV difere do PyTorch em até {worst:.3f}. Não use este modelo.")
    print(f"Conferido: o OpenCV lê o ONNX e dá a mesma resposta do PyTorch (diferença máx. {worst:.4f}).")


def _save_fold_outputs(output_folder: Path, folds: List[FoldResult]) -> None:
    for index, fold in enumerate(folds, start=1):
        save_image(learning_curve_image(fold.history, fold.best_epoch), output_folder / f"curva_dobra_{index}.png")
        _save_history(output_folder / f"historico_dobra_{index}.csv", fold.history)
    errors_folder = output_folder / "erros_validacao"
    errors_folder.mkdir(parents=True, exist_ok=True)
    for old_image in errors_folder.glob("*.png"):
        old_image.unlink()
    for prediction in (p for fold in folds for p in fold.predictions if not p.is_correct()):
        name = (f"{prediction.sample.name}_real-{CLASS_NAMES[prediction.sample.label]}"
                f"_cnn-{CLASS_NAMES[prediction.predicted_label]}_p{prediction.defect_probability:.2f}.png")
        save_image(prediction.sample.crop_bgr, errors_folder / name)


def _save_history(destination: Path, history: List[EpochRecord]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["epoca", "perda_treino", "perda_validacao", "acuracia_balanceada_validacao"])
        for record in history:
            values = (record.train_loss, record.validation_loss, record.validation_balanced_accuracy)
            writer.writerow([record.epoch, *(f"{value:.4f}".replace(".", ",") for value in values)])


_METRIC_NAMES = ("accuracy", "balanced_accuracy", "recall", "specificity", "f1")


class CnnReportBuilder:
    """Monta o RELATORIO.md por partes (Builder)."""

    def __init__(self, samples: List[CropSample]):
        self.summary = ""
        self._lines = ["# Treino da CNN de defeitos (sadio x com defeito)", "",
                       "Rede: ResNet-18 pré-treinada no ImageNet e ajustada às fotos da bancada (transferência "
                       "de aprendizado). Entrada: recorte 224x224 do tomate, com balanço de branco.",
                       "Divisão sempre **por tomate**: fotos do mesmo tomate nunca ficam em treino e validação.", "",
                       "## Dataset", "", "| Classe | Fotos | Tomates |", "|---|---|---|"]
        for label, name in enumerate(CLASS_NAMES):
            of_class = [s for s in samples if s.label == label]
            self._lines.append(f"| {name} | {len(of_class)} | {len({s.tomato_id for s in of_class})} |")
        self._lines.append("")

    def add_cross_validation(self, folds: List[FoldResult]) -> None:
        self._lines += [f"## Validação cruzada ({len(folds)} dobras por tomate)", "",
                        "Cada dobra treina uma rede nova e valida em tomates que ela nunca viu. "
                        "A média e o desvio padrão são a estimativa do desempenho em tomates novos.", "",
                        "| Dobra | Fotos | Melhor época | Acurácia | Acurácia balanceada | Sensibilidade (acha defeito) "
                        "| Especificidade (passa sadio) | F1 |", "|---|---|---|---|---|---|---|---|"]
        for index, fold in enumerate(folds, start=1):
            self._lines.append(f"| {index} | {fold.metrics.total} | {fold.best_epoch} | {_metric_cells(fold.metrics)} |")
        means = [np.mean([getattr(fold.metrics, name)() for fold in folds]) for name in _METRIC_NAMES]
        deviations = [np.std([getattr(fold.metrics, name)() for fold in folds]) for name in _METRIC_NAMES]
        self._lines.append("| **Média** | | | " + " | ".join(f"**{v:.1%}**" for v in means) + " |")
        self._lines.append("| Desvio padrão | | | " + " | ".join(f"{v:.1%}" for v in deviations) + " |")
        total = _metrics_of([p for fold in folds for p in fold.predictions])
        self._lines += ["", "Matriz de confusão somando as dobras (cada foto aparece uma vez, como validação):", "",
                        "| Real \\ CNN | sadio | com_defeito |", "|---|---|---|",
                        f"| sadio | {total.true_negatives} | {total.false_positives} |",
                        f"| com_defeito | {total.false_negatives} | {total.true_positives} |", "",
                        "Curvas de aprendizado: `curva_dobra_N.png` (e `historico_dobra_N.csv`). "
                        "Recortes errados: `erros_validacao/` (p = probabilidade de defeito dada pela CNN).", ""]
        self.summary = (f"Validação cruzada: acurácia balanceada {means[1]:.1%} ± {deviations[1]:.1%}, "
                        f"sensibilidade {means[2]:.1%}, especificidade {means[3]:.1%}.")

    def add_final_model(self, final_epochs: int, maximum_epochs: int) -> None:
        self._lines += ["## Modelo final (`cnn_defeito.onnx`, usado na IHM)", "",
                        f"Treinado com **todos** os tomates por {final_epochs} épocas (mediana da melhor época das "
                        f"dobras, de no máximo {maximum_epochs}). Com poucos tomates com defeito, separar alguns só "
                        "para escolher a época tiraria exemplos que fazem falta; o desempenho esperado é o da "
                        "validação cruzada acima.", "",
                        "> O resultado definitivo é o do conjunto de teste (2º lote), avaliado uma única vez.", ""]

    def text(self) -> str:
        return "\n".join(self._lines) + "\n"


def _metric_cells(metrics: BinaryMetrics) -> str:
    return " | ".join(f"{getattr(metrics, name)():.1%}" for name in _METRIC_NAMES)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m calibracao_branco.defect_training_cli",
                                     description="Treina a CNN sadio x com defeito com as fotos de Dataset-proprio.")
    parser.add_argument("--gain", default="bancada.gain", help="Ganhos do branco e região de interesse.")
    parser.add_argument("--pasta", default="../Dataset-proprio", help="Pasta com fotos/ e rotulos.csv.")
    parser.add_argument("--saida", default="cnn_defeito.onnx", help="Modelo exportado para a IHM.")
    parser.add_argument("--epocas", type=int, default=30, help="Máximo de épocas em cada dobra.")
    parser.add_argument("--dobras", type=int, default=5, help="Dobras da validação cruzada por tomate.")
    return parser


if __name__ == "__main__":
    sys.exit(main())
