"""Desenhos sobre a imagem para o operador conferir a calibração de escala."""

import cv2
import numpy as np

from .camera import FrameSource
from .chessboard import ChessboardDetection
from .drawing import draw_rectangle, draw_text_block, line_thickness
from .pixel_scale import PixelScaleMap
from .region import RegionOfInterest
from .scale_file import ERROR_TOLERANCE_MM

REGION_COLOR = (0, 255, 255)
CELL_OK_COLOR = (0, 200, 0)
CELL_ABOVE_TOLERANCE_COLOR = (0, 0, 255)
CORNER_COLOR = (255, 0, 255)


class RegionOverlayFrameSourceDecorator:
    """Entrega os quadros da câmera com a região de interesse desenhada.

    Serve só para o operador posicionar o alvo; a medição usa a câmera
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
    draw_rectangle(drawn, region, REGION_COLOR)
    return drawn


def draw_scale_map(frame: np.ndarray, detection: ChessboardDetection, scale_map: PixelScaleMap) -> np.ndarray:
    """Cantos detectados + células coloridas (verde = dentro da tolerância, vermelho = fora) + mm/pixel."""
    drawn = frame.copy()
    for corner in detection.corners.reshape(-1, 2):
        cv2.circle(drawn, (int(round(corner[0])), int(round(corner[1]))), line_thickness(frame) + 1, CORNER_COLOR, -1)
    for cell_scale in scale_map.cell_scales:
        region = cell_scale.cell.region
        color = CELL_ABOVE_TOLERANCE_COLOR if cell_scale.max_error_mm > ERROR_TOLERANCE_MM else CELL_OK_COLOR
        draw_rectangle(drawn, region, color)
        draw_text_block(drawn, (f"{cell_scale.mm_per_pixel:.4f} mm/px", f"erro {cell_scale.max_error_mm:.2f} mm"),
                        (region.x + 2, region.y + 2))
    return draw_region(drawn, scale_map.grid.region)
