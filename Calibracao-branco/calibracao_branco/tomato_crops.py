"""Recorte quadrado de um tomate, a entrada da CNN de defeitos.

O mesmo recorte é usado no treino e na operação (IHM): se fossem diferentes,
a CNN veria na bancada imagens de um jeito que nunca viu no treino.
O fundo não é apagado: uma podridão escura na borda do tomate pode ter ficado
fora da máscara, e apagá-la esconderia justamente o defeito.
"""

import cv2
import numpy as np

from .channels import ChannelValues
from .errors import NoObjectFoundError
from .gain_file import apply_gains
from .region import RegionOfInterest
from .segmentation import SegmentedObject, tomato_segmenter

CROP_SIZE_PX = 224
CROP_MARGIN_FRACTION = 0.15


def crop_around(image: np.ndarray, tomato: SegmentedObject) -> np.ndarray:
    x, y, width, height = cv2.boundingRect(tomato.contour)
    side = round(max(width, height) * (1 + 2 * CROP_MARGIN_FRACTION))
    center_x, center_y = x + width / 2, y + height / 2
    left, top = round(center_x - side / 2), round(center_y - side / 2)
    # Tomate perto da beira da foto: completa com preto, que é a cor do fundo da bancada.
    padded = cv2.copyMakeBorder(image, side, side, side, side, cv2.BORDER_CONSTANT, value=(0, 0, 0))
    square = padded[top + side:top + 2 * side, left + side:left + 2 * side]
    return cv2.resize(square, (CROP_SIZE_PX, CROP_SIZE_PX), interpolation=cv2.INTER_AREA)


class TomatoCropExtractor:
    """Foto crua da bancada -> balanço de branco -> recorte de cada tomate inteiro."""

    def __init__(self, gains: ChannelValues, region: RegionOfInterest):
        self._gains = gains
        self._region = region

    def largest_crop(self, raw_photo: np.ndarray) -> np.ndarray:
        """Para as fotos do dataset, que têm um tomate só: o maior objeto é ele."""
        balanced = apply_gains(raw_photo, self._gains)
        tomatoes = tomato_segmenter().find_objects(balanced, self._region).inside
        if not tomatoes:
            raise NoObjectFoundError("nenhum tomate inteiro dentro da região de interesse")
        return crop_around(balanced, max(tomatoes, key=SegmentedObject.area_px))
