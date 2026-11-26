"""Classes de cor de pixel e a regra de maturação do tomate (RF02, ver Classes-de-cor.md)."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Dict

import numpy as np

IMMATURE_LIMIT = 0.10   # abaixo de 10% colorido = imaturo
MATURE_LIMIT = 0.60     # acima de 60% vermelho = maduro


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


@dataclass(frozen=True)
class SurfaceColor:
    """Quanto da superfície do tomate (sem cálice) mudou de cor e quanto já está vermelho."""

    colored_fraction: float   # amarelado + rosado + vermelho
    red_fraction: float       # só vermelho

    @classmethod
    def measure(cls, class_map: np.ndarray, tomato_mask: np.ndarray) -> "SurfaceColor":
        classes = class_map[tomato_mask > 0]
        counted = classes[~np.isin(classes, IGNORED_FOR_MATURITY)]
        if counted.size == 0:
            return cls(0.0, 0.0)
        return cls(float(np.isin(counted, COLORED_CLASSES).mean()), float((counted == PixelClass.VERMELHO).mean()))

    def maturity(self) -> str:
        """Agrupamento do USDA: o início da mudança conta qualquer cor (amarelado, rosado ou vermelho),
        mas os estádios 5-6 (vermelho claro e vermelho) exigem superfície vermelha. Contar amarelado
        para "maduro" classificava um tomate todo alaranjado (de vez) como maduro."""
        if self.colored_fraction < IMMATURE_LIMIT:
            return "imaturo"
        if self.red_fraction <= MATURE_LIMIT:
            return "intermediario"
        return "maduro"


def class_counts(class_map: np.ndarray, tomato_mask: np.ndarray) -> Dict[str, int]:
    classes = class_map[tomato_mask > 0]
    return {pixel_class.label: int((classes == pixel_class).sum()) for pixel_class in PixelClass}
