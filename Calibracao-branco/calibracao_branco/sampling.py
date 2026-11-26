from dataclasses import dataclass, field
from typing import List

import numpy as np

from .camera import FrameSource
from .channels import ChannelValues
from .errors import WhiteReferenceSaturatedError, WhiteReferenceTooDarkError
from .region import RegionOfInterest

SATURATION_LEVEL = 250
MINIMUM_USEFUL_LEVEL = 60
MAXIMUM_SATURATED_FRACTION = 0.01
MAXIMUM_SPATIAL_VARIATION = 0.08


@dataclass(frozen=True)
class SamplingSettings:
    frames_to_discard: int = 15
    frames_to_average: int = 30


@dataclass(frozen=True)
class WhiteReferenceSample:
    channel_means: ChannelValues
    channel_variation: ChannelValues
    frames_averaged: int
    warnings: List[str] = field(default_factory=list)


class WhiteReferenceSampler:
    """Mede a cor média do gabarito branco a partir de vários quadros.

    Fazer a média de vários quadros reduz o ruído do sensor, que no celular
    é alto o bastante para mudar o ganho na segunda casa decimal.
    """

    def __init__(self, frame_source: FrameSource, settings: SamplingSettings):
        self._frame_source = frame_source
        self._settings = settings

    def sample(self, region: RegionOfInterest) -> WhiteReferenceSample:
        self._discard_warm_up_frames()
        averaged_region = self._average_region_over_frames(region)
        _ensure_not_saturated(averaged_region)
        channel_means = ChannelValues.from_bgr(averaged_region.mean(axis=(0, 1)))
        _ensure_bright_enough(channel_means)
        channel_variation = _spatial_variation(averaged_region, channel_means)
        return WhiteReferenceSample(
            channel_means=channel_means,
            channel_variation=channel_variation,
            frames_averaged=self._settings.frames_to_average,
            warnings=_uniformity_warnings(channel_variation),
        )

    def _discard_warm_up_frames(self) -> None:
        # A câmera do celular leva alguns quadros para estabilizar exposição e stream.
        for _ in range(self._settings.frames_to_discard):
            self._frame_source.read_frame()

    def _average_region_over_frames(self, region: RegionOfInterest) -> np.ndarray:
        accumulated = np.zeros((region.height, region.width, 3), dtype=np.float64)
        for _ in range(self._settings.frames_to_average):
            accumulated += region.crop(self._frame_source.read_frame())
        return accumulated / self._settings.frames_to_average


def _ensure_not_saturated(averaged_region: np.ndarray) -> None:
    saturated_pixels = np.any(averaged_region >= SATURATION_LEVEL, axis=2)
    saturated_fraction = float(saturated_pixels.mean())
    if saturated_fraction > MAXIMUM_SATURATED_FRACTION:
        raise WhiteReferenceSaturatedError(
            f"{saturated_fraction:.1%} do gabarito está estourado (>= {SATURATION_LEVEL}). "
            "Reduza a exposição ou a intensidade da luz: com canal estourado o ganho fica errado."
        )


def _ensure_bright_enough(channel_means: ChannelValues) -> None:
    if channel_means.lowest() < MINIMUM_USEFUL_LEVEL:
        raise WhiteReferenceTooDarkError(
            f"O canal mais escuro do gabarito tem média {channel_means.lowest():.1f} "
            f"(mínimo {MINIMUM_USEFUL_LEVEL}). Aumente a exposição ou a luz para não amplificar ruído."
        )


def _spatial_variation(averaged_region: np.ndarray, channel_means: ChannelValues) -> ChannelValues:
    standard_deviation = averaged_region.std(axis=(0, 1))
    return ChannelValues.from_bgr(standard_deviation / channel_means.to_bgr_array())


def _uniformity_warnings(channel_variation: ChannelValues) -> List[str]:
    if channel_variation.highest() <= MAXIMUM_SPATIAL_VARIATION:
        return []
    return [
        f"Gabarito pouco uniforme (variação de {channel_variation.highest():.1%}). "
        "Confira se a região pegou só o branco e se a luz está difusa (sem sombra ou reflexo)."
    ]
