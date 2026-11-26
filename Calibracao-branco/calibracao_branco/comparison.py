import cv2
import numpy as np

from .channels import ChannelValues
from .gain_file import apply_gains

LABEL_COLOR = (0, 255, 255)
LABEL_OUTLINE_COLOR = (0, 0, 0)
REFERENCE_WIDTH_FOR_LABEL = 640


def build_comparison(original: np.ndarray, gains: ChannelValues) -> np.ndarray:
    """Imagem original à esquerda e corrigida à direita, na resolução da câmera."""
    return np.hstack([
        draw_label(original, "Antes"),
        draw_label(apply_gains(original, gains), "Depois"),
    ])


def draw_label(frame: np.ndarray, label: str) -> np.ndarray:
    labeled = frame.copy()
    # Escala o texto pela largura para ficar legível tanto em 640 px quanto em 1920 px.
    font_scale = frame.shape[1] / REFERENCE_WIDTH_FOR_LABEL
    position = (int(10 * font_scale), int(35 * font_scale))
    for color, thickness in ((LABEL_OUTLINE_COLOR, 5), (LABEL_COLOR, 2)):
        cv2.putText(labeled, label, position, cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                    color, max(1, int(thickness * font_scale)))
    return labeled
