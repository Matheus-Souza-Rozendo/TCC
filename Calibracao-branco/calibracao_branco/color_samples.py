"""Pixels de treino da LUT, tirados das fotos da bancada.

Os pixels do tomate vêm de dentro da máscara, um pouco encolhida: na borda o
pixel mistura tomate e fundo e ensinaria uma cor que não existe. Os pixels do
fundo vêm de fora da máscara, um pouco aumentada, e já são da classe "fundo".
"""

from dataclasses import dataclass

import cv2
import numpy as np

from .channels import ChannelValues
from .gain_file import apply_gains
from .image_files import load_image
from .labeled_capture import LabeledPhoto
from .region import RegionOfInterest
from .errors import NoObjectFoundError
from .segmentation import tomato_segmenter


@dataclass(frozen=True)
class PixelSamplingSettings:
    tomato_pixels_per_photo: int = 4000
    background_pixels_per_photo: int = 1500
    edge_margin_px: int = 4
    random_seed: int = 42


@dataclass(frozen=True)
class SegmentedPhoto:
    """Foto com o balanço de branco aplicado e a máscara de todos os tomates dela."""

    image: np.ndarray
    tomato_mask: np.ndarray


@dataclass(frozen=True)
class PhotoPixels:
    photo: LabeledPhoto
    tomato_colors: np.ndarray       # (n, 3) BGR uint8
    background_colors: np.ndarray   # (m, 3) BGR uint8


class PhotoSegmenter:
    def __init__(self, gains: ChannelValues, region: RegionOfInterest):
        self._gains = gains
        self._region = region

    def segment(self, photo: LabeledPhoto) -> SegmentedPhoto:
        image = apply_gains(load_image(photo.path), self._gains)
        tomatoes = tomato_segmenter().find_objects(image, self._region).inside
        if not tomatoes:
            raise NoObjectFoundError("nenhum tomate inteiro dentro da região de interesse")
        mask = np.zeros(image.shape[:2], np.uint8)
        # Objeto cortado pela borda (ex.: algo esquecido na beira da bancada) fica de fora.
        for segmented_object in tomatoes:
            mask = cv2.bitwise_or(mask, segmented_object.mask)
        return SegmentedPhoto(image, mask)

    def region_mask(self, shape) -> np.ndarray:
        mask = np.zeros(shape[:2], np.uint8)
        mask[self._region.y:self._region.y + self._region.height, self._region.x:self._region.x + self._region.width] = 255
        return mask


class PixelSampler:
    def __init__(self, segmenter: PhotoSegmenter, settings: PixelSamplingSettings = PixelSamplingSettings()):
        self._segmenter = segmenter
        self._settings = settings

    def sample(self, photo: LabeledPhoto) -> PhotoPixels:
        segmented = self._segmenter.segment(photo)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * self._settings.edge_margin_px + 1,) * 2)
        inner_tomato = cv2.erode(segmented.tomato_mask, kernel)
        outer_background = cv2.bitwise_and(self._segmenter.region_mask(segmented.image.shape),
                                           cv2.bitwise_not(cv2.dilate(segmented.tomato_mask, kernel, iterations=3)))
        random = np.random.default_rng(self._settings.random_seed + photo.tomato_id)
        return PhotoPixels(
            photo=photo,
            tomato_colors=_random_pixels(segmented.image, inner_tomato, self._settings.tomato_pixels_per_photo, random),
            background_colors=_random_pixels(segmented.image, outer_background,
                                             self._settings.background_pixels_per_photo, random),
        )


def _random_pixels(image: np.ndarray, mask: np.ndarray, count: int, random: np.random.Generator) -> np.ndarray:
    colors = image[mask > 0]
    if len(colors) <= count:
        return colors
    return colors[random.choice(len(colors), size=count, replace=False)]
