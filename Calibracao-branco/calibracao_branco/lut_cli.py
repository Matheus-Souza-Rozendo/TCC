"""Gera a LUT de cor a partir das fotos rotuladas: python -m calibracao_branco.lut_cli --help

1. Segmenta o tomate em cada foto e pega uma amostra dos pixels (o fundo vira a classe "fundo").
2. Agrupa os pixels do tomate por cor (k-means) e o operador diz o nome de cada grupo.
3. Treina a MLP com os pixels, separando tomates para validação.
4. Gera a LUT (256³ cores) e confere a maturação calculada em cada foto contra a informada.
"""

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple

import cv2
import numpy as np

from .color_classes import PixelClass, class_counts, colored_fraction, maturity_from_fraction
from .color_groups import DISCARD, NAME_CHOICES, ColorGroups, cluster_colors, group_panel
from .color_lut import (PixelColorClassifier, apply_lut, balanced_subsample, build_lut, class_map_image,
                        save_lut)
from .color_samples import PhotoPixels, PhotoSegmenter, PixelSampler, SegmentedPhoto
from .errors import CalibrationError
from .gain_file import GainFileReader
from .image_files import save_image
from .labeled_capture import LabeledPhoto, LabeledPhotoStore

PIXELS_PER_CLASS_FOR_TRAINING = 20000
VALIDATION_FRACTION = 0.2
MINIMUM_TOMATOES_PER_MATURITY_FOR_VALIDATION = 3
MATURITIES = ("imaturo", "intermediario", "maduro")
CONFERENCE_MARGIN_PX = 20


@dataclass(frozen=True)
class PhotoEvaluation:
    photo: LabeledPhoto
    is_validation: bool
    colored_fraction: float
    predicted_maturity: str
    pixel_counts: Dict[str, int]

    def is_correct(self) -> bool:
        return self.photo.maturity == self.predicted_maturity


def main(arguments: List[str] = None) -> int:
    options = _build_parser().parse_args(arguments)
    try:
        _run(options)
    except (CalibrationError, ValueError) as error:
        print(f"ERRO: {error}", file=sys.stderr)
        return 1
    return 0


def _run(options: argparse.Namespace) -> None:
    gain_file, dataset_folder = Path(options.gain), Path(options.pasta)
    output_folder = dataset_folder / "lut"
    segmenter = PhotoSegmenter(GainFileReader().read_gains(gain_file), GainFileReader().read_region(gain_file))
    photos = _photos_with_maturity(LabeledPhotoStore(dataset_folder))
    sampled = _sample_photos(PixelSampler(segmenter), photos)

    groups = _named_groups(sampled, segmenter, options)
    colors, classes, tomato_ids = _training_pixels(sampled, groups)
    validation_tomatoes = _choose_validation_tomatoes(photos)
    is_validation = np.isin(tomato_ids, list(validation_tomatoes))

    print(f"\nTreinando a MLP com {np.count_nonzero(~is_validation)} pixels "
          f"({len({p.tomato_id for p in photos}) - len(validation_tomatoes)} tomates de treino)...")
    classifier = PixelColorClassifier().fit(*balanced_subsample(colors[~is_validation], classes[~is_validation],
                                                                PIXELS_PER_CLASS_FOR_TRAINING))
    if is_validation.any():
        accuracy = (classifier.predict(colors[is_validation]) == classes[is_validation]).mean()
        print(f"Acerto por pixel nos tomates de validação: {accuracy:.1%}")

    print("Gerando a LUT (256³ cores)...")
    lut = build_lut(classifier)
    save_lut(lut, Path(options.saida))
    print(f"LUT salva em: {Path(options.saida).resolve()}")

    conference = LutConference(lut, segmenter, output_folder / "conferencia")
    evaluations = [conference.evaluate(photo, photo.tomato_id in validation_tomatoes) for photo in photos]
    report = _write_report(evaluations, output_folder / "RELATORIO.md")
    print(report)


def _photos_with_maturity(store: LabeledPhotoStore) -> List[LabeledPhoto]:
    photos = [photo for photo in store.labeled_photos() if photo.maturity]
    if not photos:
        raise CalibrationError("Nenhuma foto com maturação informada. Use o capturar_dataset.bat e informe 1, 2 ou 3.")
    present = {photo.maturity for photo in photos}
    missing = [maturity for maturity in MATURITIES if maturity not in present]
    if missing:
        print(f"AVISO: não há fotos de: {', '.join(missing)}. A LUT não vai aprender bem essas cores.")
    return photos


def _sample_photos(sampler: PixelSampler, photos: List[LabeledPhoto]) -> List[PhotoPixels]:
    sampled = []
    for photo in photos:
        try:
            sampled.append(sampler.sample(photo))
        except CalibrationError as error:
            print(f"AVISO: {photo.path.name} ignorada ({str(error).splitlines()[0]})")
    if not sampled:
        raise CalibrationError("Nenhuma foto pôde ser segmentada.")
    print(f"{len(sampled)} foto(s) segmentada(s).")
    return sampled


def _named_groups(sampled: List[PhotoPixels], segmenter: PhotoSegmenter, options: argparse.Namespace) -> ColorGroups:
    names_file = Path(options.pasta) / "lut" / "grupos.json"
    if names_file.is_file() and not options.reagrupar:
        print(f"Usando os nomes de grupos já salvos em {names_file} (use --reagrupar para refazer).")
        return ColorGroups.load(names_file)
    groups = cluster_colors(np.vstack([photo.tomato_colors for photo in sampled]), options.grupos)
    panel_file = names_file.with_name("grupos.png")
    save_image(group_panel(groups, [segmenter.segment(photo.photo) for photo in sampled]), panel_file)
    _open_for_viewing(panel_file)
    named = groups.with_names(_ask_group_names(len(groups.centers_lab), panel_file))
    named.save(names_file)
    return named


def _open_for_viewing(image_file: Path) -> None:
    # Abre no visualizador do Windows: a janela continua respondendo enquanto o terminal espera a digitação.
    if hasattr(os, "startfile"):
        os.startfile(image_file.resolve())


def _ask_group_names(group_count: int, panel_file: Path) -> List[str]:
    choices = " | ".join(f"{key}={name}" for key, name in NAME_CHOICES.items())
    print(f"\nVeja os grupos em {panel_file.resolve()}")
    print(f"Diga o que é cada grupo: {choices}")
    print("(reflexo de luz ou cor estranha: 0 = descartar)")
    names = []
    for group in range(1, group_count + 1):
        answer = input(f"  Grupo {group}: ").strip()
        while answer not in NAME_CHOICES:
            answer = input(f"  Opção inválida. Grupo {group} ({choices}): ").strip()
        names.append(NAME_CHOICES[answer])
    return names


def _training_pixels(sampled: List[PhotoPixels], groups: ColorGroups) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    class_by_name = {pixel_class.label: pixel_class for pixel_class in PixelClass}
    colors, classes, tomato_ids = [], [], []
    for photo_pixels in sampled:
        names = np.array(groups.names)[groups.assign(photo_pixels.tomato_colors)]
        kept = names != DISCARD
        photo_classes = np.array([class_by_name[name] for name in names[kept]], np.uint8)
        photo_colors = np.vstack([photo_pixels.tomato_colors[kept], photo_pixels.background_colors])
        photo_classes = np.concatenate([photo_classes, np.full(len(photo_pixels.background_colors), PixelClass.FUNDO)])
        colors.append(photo_colors)
        classes.append(photo_classes)
        tomato_ids.append(np.full(len(photo_colors), photo_pixels.photo.tomato_id))
    return np.vstack(colors), np.concatenate(classes), np.concatenate(tomato_ids)


def _choose_validation_tomatoes(photos: List[LabeledPhoto]) -> Set[int]:
    """Separa ~20% dos tomates de cada maturação. Por tomate, nunca por foto (evita vazamento)."""
    random = np.random.default_rng(42)
    chosen = set()
    for maturity in MATURITIES:
        tomatoes = sorted({photo.tomato_id for photo in photos if photo.maturity == maturity})
        if len(tomatoes) >= MINIMUM_TOMATOES_PER_MATURITY_FOR_VALIDATION:
            count = max(1, round(VALIDATION_FRACTION * len(tomatoes)))
            chosen.update(int(t) for t in random.choice(tomatoes, size=count, replace=False))
    if not chosen:
        print(f"AVISO: menos de {MINIMUM_TOMATOES_PER_MATURITY_FOR_VALIDATION} tomates por maturação; "
              "sem validação separada (a conferência abaixo usa os próprios tomates do treino).")
    return chosen


class LutConference:
    """Aplica a LUT em cada foto, calcula a maturação pela regra do RF02 e salva a imagem de conferência."""

    def __init__(self, lut: np.ndarray, segmenter: PhotoSegmenter, images_folder: Path):
        self._lut = lut
        self._segmenter = segmenter
        self._images_folder = images_folder

    def evaluate(self, photo: LabeledPhoto, is_validation: bool) -> PhotoEvaluation:
        segmented = self._segmenter.segment(photo)
        class_map = apply_lut(self._lut, segmented.image)
        fraction = colored_fraction(class_map, segmented.tomato_mask)
        save_image(_conference_image(segmented, class_map), self._images_folder / f"{photo.path.stem}.png")
        return PhotoEvaluation(photo, is_validation, fraction, maturity_from_fraction(fraction),
                               class_counts(class_map, segmented.tomato_mask))


def _conference_image(segmented: SegmentedPhoto, class_map: np.ndarray) -> np.ndarray:
    """Foto do tomate à esquerda e as classes da LUT à direita (fora do tomate fica preto)."""
    x, y, width, height = cv2.boundingRect(segmented.tomato_mask)
    top, left = max(0, y - CONFERENCE_MARGIN_PX), max(0, x - CONFERENCE_MARGIN_PX)
    bottom, right = y + height + CONFERENCE_MARGIN_PX, x + width + CONFERENCE_MARGIN_PX
    colored = class_map_image(class_map)[top:bottom, left:right]
    colored[segmented.tomato_mask[top:bottom, left:right] == 0] = 0
    return np.hstack([segmented.image[top:bottom, left:right], colored])


def _write_report(evaluations: List[PhotoEvaluation], destination: Path) -> str:
    lines = ["# Conferência da LUT de cor", "",
             "Maturação calculada pela regra do RF02 (% colorido = amarelado + rosado + vermelho, sem cálice) "
             "contra a maturação informada na captura.", ""]
    for title, subset in (("Tomates de validação (não usados no treino da MLP)", [e for e in evaluations if e.is_validation]),
                          ("Tomates de treino (só conferência: a MLP já viu esses pixels)", [e for e in evaluations if not e.is_validation])):
        if subset:
            lines += [f"## {title}", "", *_confusion_table(subset), ""]
    lines += ["## Por foto", "", "| Foto | Tomate | Conjunto | Informada | % colorido | Calculada | Acerto |",
              "|---|---|---|---|---|---|---|"]
    for e in evaluations:
        lines.append(f"| {e.photo.path.name} | {e.photo.tomato_id} | {'validação' if e.is_validation else 'treino'} | "
                     f"{e.photo.maturity} | {e.colored_fraction:.0%} | {e.predicted_maturity} | "
                     f"{'sim' if e.is_correct() else '**não**'} |")
    lines += ["", "Imagens de conferência (foto | classes da LUT) em `conferencia/`. Cores: verde = verde, "
              "amarelo = amarelado, rosa = rosado, vermelho = vermelho, verde-escuro = cálice."]
    report = "\n".join(lines) + "\n"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(report, encoding="utf-8")
    return report


def _confusion_table(evaluations: List[PhotoEvaluation]) -> List[str]:
    accuracy = np.mean([e.is_correct() for e in evaluations])
    lines = [f"Acerto: **{accuracy:.0%}** ({sum(e.is_correct() for e in evaluations)} de {len(evaluations)} fotos)", "",
             "| Informada \\ Calculada | " + " | ".join(MATURITIES) + " |", "|---|" + "---|" * len(MATURITIES)]
    for informed in MATURITIES:
        counts = [sum(1 for e in evaluations if e.photo.maturity == informed and e.predicted_maturity == predicted)
                  for predicted in MATURITIES]
        lines.append(f"| {informed} | " + " | ".join(str(c) for c in counts) + " |")
    return lines


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m calibracao_branco.lut_cli",
                                     description="Gera a LUT de cor (MLP) a partir das fotos rotuladas da bancada.")
    parser.add_argument("--gain", default="bancada.gain", help="Ganhos do branco e região de interesse.")
    parser.add_argument("--pasta", default="../Dataset-cor", help="Pasta com fotos/ e rotulos.csv (capturar_dataset).")
    parser.add_argument("--saida", default="lut_cor.npz", help="Arquivo da LUT gerada.")
    parser.add_argument("--grupos", type=int, default=8, help="Quantos grupos de cor no k-means.")
    parser.add_argument("--reagrupar", action="store_true", help="Refaz os grupos e pergunta os nomes de novo.")
    return parser


if __name__ == "__main__":
    sys.exit(main())
