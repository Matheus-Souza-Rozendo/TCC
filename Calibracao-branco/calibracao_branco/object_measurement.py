"""Tamanho de objetos circulares (moeda, tomate) em pixels e em mm.

O diâmetro vem da área: é o diâmetro do círculo com a mesma área do objeto.
Isso usa todos os pixels do contorno, então é menos sensível a um serrilhado
na borda do que ajustar um círculo em poucos pontos.

Correção por região: cada pixel do objeto vale (mm/px da célula onde ele
está)² em mm². Somando, chega-se à área real mesmo quando o objeto fica em
cima da divisa entre células com escalas diferentes.
"""

import math
from dataclasses import dataclass
from typing import List, Tuple

import cv2
import numpy as np

from .errors import ObjectTouchesRegionBorderError
from .pixel_scale import PixelScaleMap
from .segmentation import SegmentedObject

MINIMUM_CIRCULARITY = 0.85


@dataclass(frozen=True)
class CellShare:
    cell_label: str
    fraction: float


@dataclass(frozen=True)
class ObjectMeasurement:
    center: Tuple[float, float]
    area_px: int
    diameter_px: float
    diameter_mm_single_scale: float
    diameter_mm_region_corrected: float
    circularity: float
    cell_shares: List[CellShare]

    def looks_circular(self) -> bool:
        return self.circularity >= MINIMUM_CIRCULARITY


class CircularObjectMeasurer:
    def __init__(self, scale_map: PixelScaleMap):
        self._scale_map = scale_map

    def measure(self, segmented_object: SegmentedObject) -> ObjectMeasurement:
        area_px = segmented_object.area_px()
        pixel_counts = self._pixel_count_per_cell(segmented_object.mask)
        if sum(count for _, count, _ in pixel_counts) < area_px:
            raise ObjectTouchesRegionBorderError("Parte do objeto está fora da região calibrada.")
        area_mm2 = sum(count * mm_per_pixel ** 2 for _, count, mm_per_pixel in pixel_counts)
        diameter_px = equivalent_diameter(area_px)
        return ObjectMeasurement(
            center=_centroid(segmented_object.contour),
            area_px=area_px,
            diameter_px=diameter_px,
            diameter_mm_single_scale=diameter_px * self._scale_map.mean_mm_per_pixel(),
            diameter_mm_region_corrected=equivalent_diameter(area_mm2),
            circularity=_circularity(area_px, segmented_object.perimeter_px()),
            cell_shares=[CellShare(label, count / area_px) for label, count, _ in pixel_counts if count > 0],
        )

    def _pixel_count_per_cell(self, mask: np.ndarray) -> List[Tuple[str, int, float]]:
        return [
            (cell_scale.cell.label(), int(np.count_nonzero(cell_scale.cell.region.crop(mask))), cell_scale.mm_per_pixel)
            for cell_scale in self._scale_map.cell_scales
        ]


def equivalent_diameter(area: float) -> float:
    return math.sqrt(4 * area / math.pi)


def _circularity(area_px: int, perimeter_px: float) -> float:
    """1,0 para um círculo perfeito; menor para formas alongadas ou irregulares."""
    return 4 * math.pi * area_px / perimeter_px ** 2 if perimeter_px > 0 else 0.0


def _centroid(contour: np.ndarray) -> Tuple[float, float]:
    moments = cv2.moments(contour)
    return moments["m10"] / moments["m00"], moments["m01"] / moments["m00"]
