from pathlib import Path

import cv2
import numpy as np

from .channels import ChannelValues
from .errors import CalibrationError
from .gain_file import apply_gains

LABEL_COLOR = (0, 255, 255)
LABEL_OUTLINE_COLOR = (0, 0, 0)
REFERENCE_WIDTH_FOR_LABEL = 640


def build_comparison(original: np.ndarray, gains: ChannelValues) -> np.ndarray:
    """Imagem original à esquerda e corrigida à direita, na resolução da câmera."""
    return np.hstack([
        _with_label(original, "Antes"),
        _with_label(apply_gains(original, gains), "Depois"),
    ])


def save_image(image: np.ndarray, destination: Path) -> None:
    # cv2.imwrite falha em silêncio com acentos no caminho no Windows;
    # codificar em memória e gravar pelo Python evita isso.
    encoded_successfully, encoded = cv2.imencode(destination.suffix or ".png", image)
    if not encoded_successfully:
        raise CalibrationError(f"Formato de imagem não suportado: '{destination.suffix}'. Use .png ou .jpg.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(encoded.tobytes())


def _with_label(frame: np.ndarray, label: str) -> np.ndarray:
    labeled = frame.copy()
    # Escala o texto pela largura para ficar legível tanto em 640 px quanto em 1920 px.
    font_scale = frame.shape[1] / REFERENCE_WIDTH_FOR_LABEL
    position = (int(10 * font_scale), int(35 * font_scale))
    for color, thickness in ((LABEL_OUTLINE_COLOR, 5), (LABEL_COLOR, 2)):
        cv2.putText(labeled, label, position, cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                    color, max(1, int(thickness * font_scale)))
    return labeled
