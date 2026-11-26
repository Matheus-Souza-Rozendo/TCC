"""Separa os objetos do fundo preto (tecido corvin), só dentro da região de interesse."""

from dataclasses import dataclass
from typing import List, Protocol

import cv2
import numpy as np

from .errors import NoObjectFoundError, ObjectTouchesRegionBorderError
from .region import RegionOfInterest


@dataclass(frozen=True)
class SegmentationSettings:
    blur_kernel_size: int = 5
    opening_kernel_size: int = 5
    closing_kernel_size: int = 9
    minimum_area_fraction: float = 0.002
    minimum_contrast: float = 40.0


class BrightnessChannelStrategy(Protocol):
    """Qual imagem de "brilho" separa o objeto do fundo."""

    def brightness(self, bgr_image: np.ndarray) -> np.ndarray: ...


class GrayChannelStrategy:
    """Cinza comum: bom para objetos claros e neutros, como a moeda."""

    def brightness(self, bgr_image: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)


class BrightestChannelStrategy:
    """Maior canal de cada pixel. Tomate vermelho tem cinza baixo (pouco verde e azul), mas o
    vermelho é alto; com o cinza, um objeto branco na cena "rouba" o limiar e o tomate some."""

    def brightness(self, bgr_image: np.ndarray) -> np.ndarray:
        return bgr_image.max(axis=2)


@dataclass(frozen=True)
class SegmentedObject:
    """Um objeto encontrado. Contorno e máscara já estão nas coordenadas da imagem inteira."""

    contour: np.ndarray
    mask: np.ndarray

    def area_px(self) -> int:
        return int(np.count_nonzero(self.mask))

    def perimeter_px(self) -> float:
        return float(cv2.arcLength(self.contour, closed=True))


@dataclass(frozen=True)
class SegmentationResult:
    """Objetos inteiros dentro da região e quantos ficaram cortados pela borda (não dá para medir)."""

    inside: List[SegmentedObject]
    touching_border_count: int


class ObjectSegmenter(Protocol):
    def segment(self, frame: np.ndarray, region: RegionOfInterest) -> List[SegmentedObject]: ...


class DarkBackgroundSegmenter:
    """Objeto claro sobre fundo escuro.

    O limiar é escolhido sozinho (Otsu) a cada imagem, então funciona mesmo que a
    luz mude um pouco. Buracos internos (reflexo escuro na moeda, por exemplo) são
    preenchidos, porque o tamanho é medido pelo contorno externo.
    """

    def __init__(self, channel: BrightnessChannelStrategy = GrayChannelStrategy(),
                 settings: SegmentationSettings = SegmentationSettings()):
        self._channel = channel
        self._settings = settings

    def segment(self, frame: np.ndarray, region: RegionOfInterest) -> List[SegmentedObject]:
        """Para medir com rigor: falha se não houver objeto ou se algum estiver cortado pela borda."""
        result = self.find_objects(frame, region)
        if result.touching_border_count:
            raise ObjectTouchesRegionBorderError(
                "Um objeto está encostando na borda da região de interesse e seria medido cortado.\n"
                "  - Mova o objeto para dentro da área amarela."
            )
        if not result.inside:
            raise NoObjectFoundError(
                "Nenhum objeto claro encontrado sobre o fundo preto na região de interesse.\n"
                "  - Confira se o objeto está dentro da área amarela e se a luz está ligada."
            )
        return result.inside

    def find_objects(self, frame: np.ndarray, region: RegionOfInterest) -> SegmentationResult:
        """Para a operação contínua: cena vazia ou objeto na borda não são erro, só são informados."""
        brightness = self._channel.brightness(region.crop(frame))
        foreground = self._foreground_mask(brightness)
        contours, _ = cv2.findContours(foreground, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        minimum_area = self._settings.minimum_area_fraction * region.width * region.height
        candidates = [contour for contour in contours if cv2.contourArea(contour) >= minimum_area]
        objects = [contour for contour in candidates if self._stands_out_from_background(brightness, contour)]
        inside = [contour for contour in objects if not _touches_border(contour, region)]
        return SegmentationResult(
            inside=[_to_frame_coordinates(contour, region, frame.shape[:2]) for contour in _reading_order(inside)],
            touching_border_count=len(objects) - len(inside),
        )

    def _foreground_mask(self, brightness: np.ndarray) -> np.ndarray:
        blurred = cv2.GaussianBlur(brightness, (self._settings.blur_kernel_size,) * 2, 0)
        _, mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, _ellipse_kernel(self._settings.opening_kernel_size))
        return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, _ellipse_kernel(self._settings.closing_kernel_size))

    def _stands_out_from_background(self, brightness: np.ndarray, contour: np.ndarray) -> bool:
        # Sem objeto, o Otsu ainda divide o ruído do fundo em "claro" e "escuro";
        # exigir contraste mínimo evita medir manchas do próprio tecido.
        object_mask = np.zeros(brightness.shape, np.uint8)
        cv2.drawContours(object_mask, [contour], -1, 255, cv2.FILLED)
        object_mean = cv2.mean(brightness, mask=object_mask)[0]
        background_mean = cv2.mean(brightness, mask=cv2.bitwise_not(object_mask))[0]
        return object_mean - background_mean >= self._settings.minimum_contrast


def _reading_order(contours: List[np.ndarray]) -> List[np.ndarray]:
    """De cima para baixo e da esquerda para a direita, para a numeração ser previsível."""
    return sorted(contours, key=lambda contour: (cv2.boundingRect(contour)[1], cv2.boundingRect(contour)[0]))


def _touches_border(contour: np.ndarray, region: RegionOfInterest) -> bool:
    x, y, width, height = cv2.boundingRect(contour)
    return x <= 0 or y <= 0 or x + width >= region.width or y + height >= region.height


def _to_frame_coordinates(contour: np.ndarray, region: RegionOfInterest, frame_shape) -> SegmentedObject:
    frame_contour = contour + np.array([region.x, region.y], dtype=contour.dtype)
    mask = np.zeros(frame_shape, np.uint8)
    cv2.drawContours(mask, [frame_contour], -1, 255, cv2.FILLED)
    return SegmentedObject(contour=frame_contour, mask=mask)


TOMATO_MINIMUM_CONTRAST = 30.0


def tomato_segmenter() -> DarkBackgroundSegmenter:
    # Contraste 30 e não 40: tomate podre/escuro fica entre 30 e 40 acima do fundo. Medido nas
    # 226 fotos do dataset: com 30 nenhuma faixa vazia do tecido virou objeto.
    return DarkBackgroundSegmenter(BrightestChannelStrategy(), SegmentationSettings(minimum_contrast=TOMATO_MINIMUM_CONTRAST))


def _ellipse_kernel(size: int) -> np.ndarray:
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
