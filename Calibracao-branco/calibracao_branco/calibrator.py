from datetime import datetime
from typing import Callable

from .gain_file import CalibrationResult
from .gain_strategies import GainStrategy
from .region import RegionOfInterest
from .sampling import WhiteReferenceSampler


class WhiteBalanceCalibrator:
    """Junta a medição do gabarito com a regra de cálculo do ganho."""

    def __init__(self, sampler: WhiteReferenceSampler, strategy: GainStrategy,
                 clock: Callable[[], datetime] = datetime.now):
        self._sampler = sampler
        self._strategy = strategy
        self._clock = clock

    def calibrate(self, region: RegionOfInterest) -> CalibrationResult:
        sample = self._sampler.sample(region)
        return CalibrationResult(
            gains=self._strategy.compute_gains(sample.channel_means),
            sample=sample,
            region=region,
            strategy_name=self._strategy.name,
            created_at=self._clock(),
        )
