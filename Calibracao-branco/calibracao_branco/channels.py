from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ChannelValues:
    """Um valor por canal de cor. A ordem é sempre explícita pelo nome,
    porque o OpenCV usa BGR e é fácil trocar R com B sem perceber."""

    red: float
    green: float
    blue: float

    @classmethod
    def from_bgr(cls, bgr_values) -> "ChannelValues":
        blue, green, red = (float(value) for value in bgr_values)
        return cls(red=red, green=green, blue=blue)

    def to_bgr_array(self) -> np.ndarray:
        return np.array([self.blue, self.green, self.red], dtype=np.float64)

    def lowest(self) -> float:
        return min(self.red, self.green, self.blue)

    def highest(self) -> float:
        return max(self.red, self.green, self.blue)
