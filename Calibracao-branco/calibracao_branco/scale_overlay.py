"""Desenhos sobre a imagem para o operador conferir a calibração de escala."""

import cv2
import numpy as np

from .camera import FrameSource
from .comparison import REFERENCE_WIDTH_FOR_LABEL
from .pixel_scale import PixelScaleMap
from .region import RegionOfInterest
from .scale_file import ERROR_TOLERANCE_MM

REGION_COLOR = (0, 255, 255)
CELL_OK_COLOR = (0, 200, 0)
CELL_ABOVE_TOLERANCE_COLOR = (0, 0, 255)
CORNER_COLOR = (255, 0, 255)
TEXT_COLOR = (255, 255, 255)
TEXT_BACKGROUND_COLOR = (40, 40, 40)


class RegionOverlayFrameSourceDecorator:
    """Entrega os quadros da câmera com a região de interesse desenhada.

    Serve só para o operador posicionar o tabuleiro; a medição usa a câmera
    original, sem o desenho.
    """

    def __init__(self, frame_source: FrameSource, region: RegionOfInterest):
        self._frame_source = frame_source
        self._region = region

    def read_frame(self) -> np.ndarray:
        return draw_region(self._frame_source.read_frame(), self._region)

    def close(self) -> None:
        self._frame_source.close()


def draw_region(frame: np.ndarray, region: RegionOfInterest) -> np.ndarray:
    drawn = frame.copy()
    cv2.rectangle(drawn, (region.x, region.y), (region.x + region.width, region.y + region.height),
                  REGION_COLOR, _line_thickness(frame))
    return drawn


def draw_scale_map(frame: np.ndarray, corners: np.ndarray, scale_map: PixelScaleMap) -> np.ndarray:
    """Cantos detectados + células coloridas (verde = dentro da tolerância, vermelho = fora) + mm/pixel."""
    drawn = frame.copy()
    for corner in corners.reshape(-1, 2):
        cv2.circle(drawn, (int(round(corner[0])), int(round(corner[1]))), _line_thickness(frame) + 1, CORNER_COLOR, -1)
    for cell_scale in scale_map.cell_scales:
        region = cell_scale.cell.region
        color = CELL_ABOVE_TOLERANCE_COLOR if cell_scale.max_error_mm > ERROR_TOLERANCE_MM else CELL_OK_COLOR
        cv2.rectangle(drawn, (region.x, region.y), (region.x + region.width, region.y + region.height),
                      color, _line_thickness(frame))
        _write_cell_values(drawn, region, cell_scale)
    return draw_region(drawn, scale_map.grid.region)


def _write_cell_values(image: np.ndarray, region: RegionOfInterest, cell_scale) -> None:
    size_factor = image.shape[1] / REFERENCE_WIDTH_FOR_LABEL
    font_scale = 0.45 * size_factor
    text_thickness = max(1, round(size_factor))
    line_height = int(18 * size_factor)
    lines = (f"{cell_scale.mm_per_pixel:.4f} mm/px", f"erro {cell_scale.max_error_mm:.2f} mm")
    widest = max(cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_thickness)[0][0] for text in lines)
    # Faixa escura atrás do texto: sem ela, o texto some sobre os quadrados brancos do tabuleiro.
    top_left = (region.x + 2, region.y + 2)
    bottom_right = (region.x + widest + 10, region.y + line_height * len(lines) + int(8 * size_factor))
    cv2.rectangle(image, top_left, bottom_right, TEXT_BACKGROUND_COLOR, -1)
    for index, text in enumerate(lines):
        position = (region.x + 6, region.y + line_height * (index + 1))
        cv2.putText(image, text, position, cv2.FONT_HERSHEY_SIMPLEX, font_scale, TEXT_COLOR, text_thickness)


def _line_thickness(frame: np.ndarray) -> int:
    return max(2, round(2 * frame.shape[1] / REFERENCE_WIDTH_FOR_LABEL))
