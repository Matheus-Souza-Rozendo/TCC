"""Janelas do OpenCV. Fica separado da lógica para que ela possa ser testada sem tela."""

import cv2
import numpy as np

from .camera import FrameSource
from .channels import ChannelValues
from .errors import CalibrationCancelledError
from .gain_file import apply_gains
from .region import RegionOfInterest

WINDOW_NAME = "Calibracao de branco"
SELECTION_WINDOW_NAME = "Arraste sobre o branco e aperte ENTER (C = cancelar)"
KEY_ESCAPE = 27
KEYS_CONFIRM = (13, 32)
TEXT_COLOR = (0, 255, 255)
DEFAULT_DISPLAY_WIDTH = 960


class CalibrationPreview:
    """Mostra as imagens numa largura fixa de tela, mantendo a proporção.

    A redução é só visual: a medição sempre usa o quadro na resolução original,
    e a região escolhida na tela é convertida de volta para ela.
    """

    def __init__(self, display_width: int = DEFAULT_DISPLAY_WIDTH):
        if display_width <= 0:
            raise ValueError("A largura da janela precisa ser maior que zero.")
        self._display_width = display_width

    def wait_for_operator_ready(self, frame_source: FrameSource) -> np.ndarray:
        """Mostra a câmera ao vivo até o operador posicionar o gabarito e apertar ENTER."""
        try:
            while True:
                frame = frame_source.read_frame()
                self._show(frame, "Posicione o gabarito branco. ENTER = continuar, ESC = sair")
                key = cv2.waitKey(1) & 0xFF
                if key in KEYS_CONFIRM:
                    return frame
                if key == KEY_ESCAPE:
                    raise CalibrationCancelledError("Calibração cancelada pelo operador.")
        finally:
            cv2.destroyWindow(WINDOW_NAME)

    def select_region(self, frame: np.ndarray) -> RegionOfInterest:
        scale = self._scale_for(frame)
        x, y, width, height = cv2.selectROI(SELECTION_WINDOW_NAME, _resized(frame, scale), showCrosshair=True)
        cv2.destroyAllWindows()
        if width == 0 or height == 0:
            raise CalibrationCancelledError("Nenhuma região do gabarito foi selecionada.")
        return RegionOfInterest(int(x), int(y), int(width), int(height)).scaled(1 / scale)

    def show_corrected_comparison(self, frame_source: FrameSource, gains: ChannelValues) -> None:
        """Mostra original e corrigido lado a lado para conferir o resultado no olho."""
        try:
            while cv2.waitKey(1) & 0xFF != KEY_ESCAPE:
                original = frame_source.read_frame()
                self._show(np.hstack([original, apply_gains(original, gains)]),
                           "Esquerda: original | Direita: corrigido | ESC = sair")
        finally:
            cv2.destroyAllWindows()

    def _show(self, frame: np.ndarray, caption: str) -> None:
        cv2.imshow(WINDOW_NAME, _with_caption(_resized(frame, self._scale_for(frame)), caption))

    def _scale_for(self, frame: np.ndarray) -> float:
        return self._display_width / frame.shape[1]


def _resized(frame: np.ndarray, scale: float) -> np.ndarray:
    height, width = frame.shape[:2]
    interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR
    return cv2.resize(frame, (round(width * scale), round(height * scale)), interpolation=interpolation)


def _with_caption(frame: np.ndarray, caption: str) -> np.ndarray:
    captioned = frame.copy()
    cv2.putText(captioned, caption, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, TEXT_COLOR, 2)
    return captioned
