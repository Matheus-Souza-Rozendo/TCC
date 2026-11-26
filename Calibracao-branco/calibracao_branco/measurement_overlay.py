"""Imagem de resultado da medição. Textos sem acento: a fonte do OpenCV não desenha ç/ã."""

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np

from .drawing import draw_rectangle, draw_text_block, line_thickness, text_block_size
from .object_measurement import ObjectMeasurement
from .pixel_scale import PixelScaleMap
from .segmentation import SegmentedObject

REGION_COLOR = (0, 255, 255)
CELL_COLOR = (110, 110, 110)
CONTOUR_COLOR = (0, 220, 0)
EQUIVALENT_CIRCLE_COLOR = (255, 200, 0)


@dataclass(frozen=True)
class MeasuredObject:
    segment: SegmentedObject
    measurement: ObjectMeasurement


class MeasurementOverlay:
    """Desenha células, contorno, círculo equivalente e os tamanhos de cada objeto."""

    def __init__(self, scale_map: PixelScaleMap, reference_diameter_mm: Optional[float]):
        self._scale_map = scale_map
        self._reference_diameter_mm = reference_diameter_mm

    def draw(self, frame: np.ndarray, measured_objects: List[MeasuredObject]) -> np.ndarray:
        drawn = frame.copy()
        for cell_scale in self._scale_map.cell_scales:
            draw_rectangle(drawn, cell_scale.cell.region, CELL_COLOR)
        draw_rectangle(drawn, self._scale_map.grid.region, REGION_COLOR)
        for number, measured in enumerate(measured_objects, start=1):
            self._draw_object(drawn, number, measured)
        return drawn

    def _draw_object(self, image: np.ndarray, number: int, measured: MeasuredObject) -> None:
        measurement = measured.measurement
        center = (int(round(measurement.center[0])), int(round(measurement.center[1])))
        radius = int(round(measurement.diameter_px / 2))
        cv2.drawContours(image, [measured.segment.contour], -1, CONTOUR_COLOR, line_thickness(image))
        cv2.circle(image, center, radius, EQUIVALENT_CIRCLE_COLOR, max(1, line_thickness(image) // 2))
        cv2.circle(image, center, line_thickness(image), EQUIVALENT_CIRCLE_COLOR, -1)
        lines = self.describe(number, measurement)
        draw_text_block(image, lines, _beside_object(image, lines, center, radius))

    def describe(self, number: int, measurement: ObjectMeasurement) -> List[str]:
        lines = [
            f"Objeto {number}: {measurement.diameter_px:.1f} px",
            f"sem correcao: {measurement.diameter_mm_single_scale:.2f} mm",
            f"com correcao: {measurement.diameter_mm_region_corrected:.2f} mm",
        ]
        if self._reference_diameter_mm is not None:
            error = measurement.diameter_mm_region_corrected - self._reference_diameter_mm
            lines.append(f"real {self._reference_diameter_mm:.2f} mm | erro {error:+.2f} mm")
        shares = " ".join(f"{share.cell_label} {share.fraction:.0%}" for share in measurement.cell_shares)
        lines.append(f"celulas: {shares}")
        circularity_note = "" if measurement.looks_circular() else " (NAO circular)"
        lines.append(f"circularidade {measurement.circularity:.2f}{circularity_note}")
        return lines


def _beside_object(image: np.ndarray, lines: List[str], center: Tuple[int, int], radius: int) -> Tuple[int, int]:
    """À direita do objeto se couber; senão à esquerda, para o texto não cobrir o objeto."""
    width, _ = text_block_size(image, lines)
    gap = radius + 8
    right_x = center[0] + gap
    x = right_x if right_x + width <= image.shape[1] else center[0] - gap - width
    return x, center[1] - radius
