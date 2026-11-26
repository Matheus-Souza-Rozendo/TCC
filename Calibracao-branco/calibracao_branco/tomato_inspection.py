"""Inspeção completa de uma imagem da bancada (padrão Facade).

A IHM só chama inspect(foto crua). Por trás: balanço de branco -> segmentação
-> para cada tomate: tamanho (escala por região), maturação (LUT) e defeito
(CNN no recorte) -> destino de separação.
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple

import numpy as np

from .channels import ChannelValues
from .defect_classifier import DefectClassifier, DefectVerdict
from .gain_file import apply_gains
from .maturity_classifier import MaturityClassifier, MaturityVerdict
from .pixel_scale import PixelScaleMap
from .segmentation import SegmentedObject, tomato_segmenter
from .tomato_crops import crop_around
from .tomato_shape import TomatoShapeMeasurer, TomatoSize


class SortingDestination(Enum):
    """Para onde o tomate vai. Valor = (título, cor de destaque em hexadecimal)."""

    MADURO = ("Maduro", "#c62828")
    INTERMEDIARIO = ("Intermediário", "#ef6c00")
    IMATURO = ("Imaturo", "#2e7d32")
    DESCARTE = ("Descarte", "#37474f")
    INDEFINIDO = ("Sem classe", "#757575")

    @property
    def title(self) -> str:
        return self.value[0]

    @property
    def color_hex(self) -> str:
        return self.value[1]

    @property
    def color_bgr(self) -> Tuple[int, int, int]:
        red, green, blue = (int(self.color_hex[i:i + 2], 16) for i in (1, 3, 5))
        return blue, green, red


_DESTINATION_BY_MATURITY = {"maduro": SortingDestination.MADURO, "intermediario": SortingDestination.INTERMEDIARIO,
                            "imaturo": SortingDestination.IMATURO}


@dataclass(frozen=True)
class TomatoInspection:
    number: int
    tomato: SegmentedObject
    size: TomatoSize
    maturity: MaturityVerdict
    defect: DefectVerdict

    def destination(self) -> SortingDestination:
        # Defeito manda para o descarte qualquer que seja a cor: tomate podre maduro não vai para a venda.
        if self.defect.has_defect():
            return SortingDestination.DESCARTE
        if not self.maturity.is_evaluated:
            return SortingDestination.INDEFINIDO
        return _DESTINATION_BY_MATURITY[self.maturity.label()]


@dataclass(frozen=True)
class InspectionReport:
    balanced_image: np.ndarray
    tomatoes: List[TomatoInspection]
    cut_by_border_count: int
    elapsed_ms: float


@dataclass(frozen=True)
class InspectionModels:
    """O que a inspeção precisa da calibração e do treino (injetado: nos testes entram versões falsas)."""

    gains: ChannelValues
    scale_map: PixelScaleMap
    maturity_classifier: MaturityClassifier
    defect_classifier: DefectClassifier


class TomatoInspectionFacade:
    def __init__(self, models: InspectionModels):
        self._models = models
        self._shape_measurer = TomatoShapeMeasurer(models.scale_map)

    @property
    def region(self):
        return self._models.scale_map.grid.region

    def inspect(self, raw_frame: np.ndarray) -> InspectionReport:
        started = time.perf_counter()
        balanced = apply_gains(raw_frame, self._models.gains)
        segmentation = tomato_segmenter().find_objects(balanced, self.region)
        tomatoes = [self._inspect_one(balanced, (number, tomato))
                    for number, tomato in enumerate(segmentation.inside, start=1)]
        return InspectionReport(balanced, tomatoes, segmentation.touching_border_count,
                                (time.perf_counter() - started) * 1000)

    def _inspect_one(self, balanced: np.ndarray, numbered_tomato: Tuple[int, SegmentedObject]) -> TomatoInspection:
        number, tomato = numbered_tomato
        return TomatoInspection(
            number=number,
            tomato=tomato,
            size=self._shape_measurer.measure(tomato),
            maturity=self._models.maturity_classifier.classify(balanced, tomato),
            defect=self._models.defect_classifier.classify(crop_around(balanced, tomato)),
        )
