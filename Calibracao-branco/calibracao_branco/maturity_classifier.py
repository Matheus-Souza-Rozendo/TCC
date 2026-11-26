"""Maturação de cada tomate pela LUT de cor (RF02)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

from .color_classes import SurfaceColor
from .color_lut import apply_lut, load_lut
from .segmentation import SegmentedObject


@dataclass(frozen=True)
class MaturityVerdict:
    is_evaluated: bool
    surface: SurfaceColor = SurfaceColor(0.0, 0.0)

    def label(self) -> str:
        return self.surface.maturity() if self.is_evaluated else "sem LUT"


class MaturityClassifier(Protocol):
    def classify(self, balanced_image: np.ndarray, tomato: SegmentedObject) -> MaturityVerdict: ...


class LutMaturityClassifier:
    def __init__(self, lut: np.ndarray):
        self._lut = lut

    def classify(self, balanced_image: np.ndarray, tomato: SegmentedObject) -> MaturityVerdict:
        # Só o retângulo do tomate passa pela LUT: a imagem inteira custaria ~10x mais por quadro.
        x, y, width, height = cv2.boundingRect(tomato.contour)
        class_map = apply_lut(self._lut, balanced_image[y:y + height, x:x + width])
        return MaturityVerdict(True, SurfaceColor.measure(class_map, tomato.mask[y:y + height, x:x + width]))


class MissingLutMaturityClassifierNullObject:
    """Sem LUT gerada a IHM continua medindo tamanho e defeito; a maturação aparece como "sem LUT"."""

    def classify(self, balanced_image: np.ndarray, tomato: SegmentedObject) -> MaturityVerdict:
        return MaturityVerdict(False)


def maturity_classifier_for(lut_file: Path) -> MaturityClassifier:
    if lut_file.is_file():
        return LutMaturityClassifier(load_lut(lut_file))
    return MissingLutMaturityClassifierNullObject()

