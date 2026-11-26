"""Desenhos comuns das imagens de conferência, com tamanho proporcional à resolução."""

from typing import Sequence, Tuple

import cv2
import numpy as np

from .region import RegionOfInterest

REFERENCE_WIDTH = 640
TEXT_COLOR = (255, 255, 255)
TEXT_BACKGROUND_COLOR = (40, 40, 40)
FONT = cv2.FONT_HERSHEY_SIMPLEX


def size_factor(image: np.ndarray) -> float:
    """1.0 numa imagem de 640 px de largura; textos e linhas crescem junto com a resolução."""
    return image.shape[1] / REFERENCE_WIDTH


def line_thickness(image: np.ndarray) -> int:
    return max(2, round(2 * size_factor(image)))


def draw_rectangle(image: np.ndarray, region: RegionOfInterest, color: Tuple[int, int, int]) -> None:
    cv2.rectangle(image, (region.x, region.y), (region.x + region.width, region.y + region.height),
                  color, line_thickness(image))


def text_block_size(image: np.ndarray, lines: Sequence[str]) -> Tuple[int, int]:
    """Largura e altura, em pixels, que draw_text_block vai ocupar."""
    font_scale, thickness, line_height = _text_metrics(image)
    widest = max(cv2.getTextSize(text, FONT, font_scale, thickness)[0][0] for text in lines)
    return widest + 10, line_height * len(lines) + int(8 * size_factor(image))


def draw_text_block(image: np.ndarray, lines: Sequence[str], top_left: Tuple[int, int]) -> None:
    """Texto sobre uma faixa escura, para continuar legível em fundo claro ou escuro."""
    font_scale, thickness, line_height = _text_metrics(image)
    width, height = text_block_size(image, lines)
    x, y = _fit_inside(image, top_left, (width, height))
    cv2.rectangle(image, (x, y), (x + width, y + height), TEXT_BACKGROUND_COLOR, -1)
    for index, text in enumerate(lines):
        cv2.putText(image, text, (x + 5, y + line_height * (index + 1)), FONT, font_scale, TEXT_COLOR, thickness)


def _text_metrics(image: np.ndarray) -> Tuple[float, int, int]:
    factor = size_factor(image)
    return 0.45 * factor, max(1, round(factor)), int(18 * factor)


def _fit_inside(image: np.ndarray, top_left: Tuple[int, int], block_size: Tuple[int, int]) -> Tuple[int, int]:
    image_height, image_width = image.shape[:2]
    x = min(max(0, top_left[0]), max(0, image_width - block_size[0]))
    y = min(max(0, top_left[1]), max(0, image_height - block_size[1]))
    return int(x), int(y)
