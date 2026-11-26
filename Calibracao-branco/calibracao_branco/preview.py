"""Janelas do OpenCV. Fica separado da lógica para que ela possa ser testada sem tela."""

import cv2
import numpy as np

from .camera import FrameSource
from .channels import ChannelValues
from .errors import CalibrationCancelledError
from .gain_file import apply_gains
from .region import RegionOfInterest

WINDOW_NAME = "Calibracao de branco"
KEY_ESCAPE = 27
KEYS_CONFIRM = (13, 32)
TEXT_COLOR = (0, 255, 255)


def wait_for_operator_ready(frame_source: FrameSource) -> np.ndarray:
    """Mostra a câmera ao vivo até o operador posicionar o gabarito e apertar ENTER."""
    try:
        while True:
            frame = frame_source.read_frame()
            cv2.imshow(WINDOW_NAME, _with_caption(frame, "Posicione o gabarito branco. ENTER = continuar, ESC = sair"))
            key = cv2.waitKey(1) & 0xFF
            if key in KEYS_CONFIRM:
                return frame
            if key == KEY_ESCAPE:
                raise CalibrationCancelledError("Calibração cancelada pelo operador.")
    finally:
        cv2.destroyWindow(WINDOW_NAME)


def select_region(frame: np.ndarray) -> RegionOfInterest:
    x, y, width, height = cv2.selectROI(
        "Arraste sobre o branco e aperte ENTER (C = cancelar)", frame, showCrosshair=True
    )
    cv2.destroyAllWindows()
    if width == 0 or height == 0:
        raise CalibrationCancelledError("Nenhuma região do gabarito foi selecionada.")
    return RegionOfInterest(int(x), int(y), int(width), int(height))


def show_corrected_comparison(frame_source: FrameSource, gains: ChannelValues) -> None:
    """Mostra original e corrigido lado a lado para conferir o resultado no olho."""
    try:
        while cv2.waitKey(1) & 0xFF != KEY_ESCAPE:
            original = frame_source.read_frame()
            comparison = np.hstack([
                _with_caption(original, "Original"),
                _with_caption(apply_gains(original, gains), "Corrigido (ESC = sair)"),
            ])
            cv2.imshow(WINDOW_NAME, comparison)
    finally:
        cv2.destroyAllWindows()


def _with_caption(frame: np.ndarray, caption: str) -> np.ndarray:
    captioned = frame.copy()
    cv2.putText(captioned, caption, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, TEXT_COLOR, 2)
    return captioned
