"""Imagem que a IHM mostra: a região de interesse ampliada, com cada tomate contornado na cor do destino."""

from typing import Tuple

import cv2
import numpy as np

from .drawing import FONT, draw_text_block, line_thickness, size_factor
from .region import RegionOfInterest
from .tomato_inspection import InspectionReport, TomatoInspection

VIEW_MARGIN_PX = 30
REGION_COLOR = (0, 215, 255)
BADGE_TEXT_COLOR = (255, 255, 255)
OUTLINE_COLOR = (255, 255, 255)


class InspectionOverlay:
    """Mostra só a região de interesse (com uma margem): fora dela nada é medido, e o tomate fica maior na tela.

    O desenho é feito já no recorte, para o tamanho do texto acompanhar o que aparece na tela.
    """

    def __init__(self, region: RegionOfInterest):
        self._region = region

    def live_view(self, frame: np.ndarray) -> np.ndarray:
        view, offset = self._crop_view(frame)
        self._draw_region(view, offset)
        return view

    def draw(self, report: InspectionReport) -> np.ndarray:
        view, offset = self._crop_view(report.balanced_image)
        self._draw_region(view, offset)
        for inspection in report.tomatoes:
            _draw_tomato(view, (inspection, offset))
        return view

    def _crop_view(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        height, width = image.shape[:2]
        left, top = max(0, self._region.x - VIEW_MARGIN_PX), max(0, self._region.y - VIEW_MARGIN_PX)
        right = min(width, self._region.x + self._region.width + VIEW_MARGIN_PX)
        bottom = min(height, self._region.y + self._region.height + VIEW_MARGIN_PX)
        return image[top:bottom, left:right].copy(), np.array([left, top])

    def _draw_region(self, view: np.ndarray, offset: np.ndarray) -> None:
        top_left = (self._region.x - offset[0], self._region.y - offset[1])
        bottom_right = (top_left[0] + self._region.width, top_left[1] + self._region.height)
        cv2.rectangle(view, top_left, bottom_right, REGION_COLOR, line_thickness(view))


def _draw_tomato(view: np.ndarray, inspection_and_offset: Tuple[TomatoInspection, np.ndarray]) -> None:
    inspection, offset = inspection_and_offset
    color = inspection.destination().color_bgr
    thickness = line_thickness(view)
    contour = inspection.tomato.contour - offset.astype(inspection.tomato.contour.dtype)
    cv2.drawContours(view, [contour], -1, OUTLINE_COLOR, thickness + 2, cv2.LINE_AA)
    cv2.drawContours(view, [contour], -1, color, thickness, cv2.LINE_AA)
    x, y, width, height = cv2.boundingRect(contour)
    _draw_number_badge(view, (inspection, (x + width // 2, y)))
    lines = [inspection.destination().title, f"{inspection.size.diameter_mm:.1f} mm".replace(".", ",")]
    draw_text_block(view, lines, (x + width + 8, y))


def _draw_number_badge(view: np.ndarray, inspection_and_position) -> None:
    inspection, (center_x, top) = inspection_and_position
    factor = size_factor(view)
    radius = round(13 * factor)
    center = (center_x, max(radius, top - radius - 4))
    cv2.circle(view, center, radius, inspection.destination().color_bgr, -1, cv2.LINE_AA)
    cv2.circle(view, center, radius, OUTLINE_COLOR, max(1, round(factor)), cv2.LINE_AA)
    text = str(inspection.number)
    scale, text_thickness = 0.55 * factor, max(1, round(1.3 * factor))
    (text_width, text_height), _ = cv2.getTextSize(text, FONT, scale, text_thickness)
    cv2.putText(view, text, (center[0] - text_width // 2, center[1] + text_height // 2), FONT, scale,
                BADGE_TEXT_COLOR, text_thickness, cv2.LINE_AA)
