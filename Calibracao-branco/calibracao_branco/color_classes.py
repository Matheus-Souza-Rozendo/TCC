"""Classes de cor de pixel e a regra de maturação do tomate (RF02, ver Classes-de-cor.md)."""

from enum import IntEnum
from typing import Dict

import numpy as np

IMMATURE_LIMIT = 0.10   # abaixo de 10% colorido = imaturo
MATURE_LIMIT = 0.60     # acima de 60% colorido = maduro


class PixelClass(IntEnum):
    VERDE = 0
    AMARELADO = 1
    ROSADO = 2
    VERMELHO = 3
    FUNDO = 4
    CALICE = 5

    @property
    def label(self) -> str:
        return self.name.lower()


COLORED_CLASSES = (PixelClass.AMARELADO, PixelClass.ROSADO, PixelClass.VERMELHO)
IGNORED_FOR_MATURITY = (PixelClass.FUNDO, PixelClass.CALICE)
# Cor de cada classe nas imagens de conferência (BGR).
DISPLAY_COLORS = {
    PixelClass.VERDE: (40, 170, 40),
    PixelClass.AMARELADO: (0, 220, 240),
    PixelClass.ROSADO: (150, 120, 255),
    PixelClass.VERMELHO: (30, 30, 220),
    PixelClass.FUNDO: (0, 0, 0),
    PixelClass.CALICE: (30, 90, 30),
}


def colored_fraction(class_map: np.ndarray, tomato_mask: np.ndarray) -> float:
    """% colorido = (amarelado + rosado + vermelho) / pixels do tomate sem cálice."""
    classes = class_map[tomato_mask > 0]
    counted = ~np.isin(classes, IGNORED_FOR_MATURITY)
    if not counted.any():
        return 0.0
    return float(np.isin(classes[counted], COLORED_CLASSES).mean())


def maturity_from_fraction(fraction: float) -> str:
    if fraction < IMMATURE_LIMIT:
        return "imaturo"
    if fraction <= MATURE_LIMIT:
        return "intermediario"
    return "maduro"


def class_counts(class_map: np.ndarray, tomato_mask: np.ndarray) -> Dict[str, int]:
    classes = class_map[tomato_mask > 0]
    return {pixel_class.label: int((classes == pixel_class).sum()) for pixel_class in PixelClass}
