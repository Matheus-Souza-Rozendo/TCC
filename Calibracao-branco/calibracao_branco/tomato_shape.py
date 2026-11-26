"""Tamanho e forma do tomate em mm: diâmetro equivalente, comprimento, largura e circularidade.

O tomate cereja do tipo "grape" é alongado, então só o diâmetro equivalente
(círculo de mesma área) não descreve bem o fruto. O comprimento e a largura
vêm do menor retângulo girado que contém o contorno (o "paquímetro" medindo
na direção do eixo maior e na perpendicular).
"""

import math
from dataclasses import dataclass
from typing import Tuple

import cv2

from .object_measurement import CircularObjectMeasurer
from .pixel_scale import PixelScaleMap
from .segmentation import SegmentedObject


@dataclass(frozen=True)
class TomatoSize:
    center: Tuple[float, float]
    diameter_mm: float        # diâmetro equivalente, com a correção de escala por região
    length_mm: float          # eixo maior
    width_mm: float           # eixo menor
    circularity: float        # 1,0 = círculo perfeito
    mm_per_pixel: float       # escala efetiva usada neste tomate

    def elongation(self) -> float:
        """Comprimento / largura: 1,0 redondo; o grape fica perto de 1,3."""
        return self.length_mm / self.width_mm if self.width_mm else 0.0


class TomatoShapeMeasurer:
    def __init__(self, scale_map: PixelScaleMap):
        self._area_measurer = CircularObjectMeasurer(scale_map)

    def measure(self, tomato: SegmentedObject) -> TomatoSize:
        measurement = self._area_measurer.measure(tomato)
        # Escala efetiva = raiz(área em mm² / área em px): já pondera as células que o tomate ocupa.
        area_mm2 = math.pi * (measurement.diameter_mm_region_corrected / 2) ** 2
        mm_per_pixel = math.sqrt(area_mm2 / measurement.area_px)
        (_, _), (side_a, side_b), _ = cv2.minAreaRect(tomato.contour)
        return TomatoSize(
            center=measurement.center,
            diameter_mm=measurement.diameter_mm_region_corrected,
            length_mm=max(side_a, side_b) * mm_per_pixel,
            width_mm=min(side_a, side_b) * mm_per_pixel,
            circularity=measurement.circularity,
            mm_per_pixel=mm_per_pixel,
        )
