"""Intervalo de confiança de 95% de uma proporção (método de Wilson).

Com poucos tomates no teste, o intervalo "p ± 1,96·erro padrão" sai de [0, 1] e fica
estreito demais perto de 0% ou 100%; o de Wilson é o recomendado por Brown, Cai e
DasGupta (2001) para amostras pequenas.
"""

import math
from dataclasses import dataclass

Z_95_PERCENT = 1.959964


@dataclass(frozen=True)
class WilsonInterval:
    successes: int
    total: int
    lower: float
    upper: float

    @classmethod
    def for_proportion(cls, successes: int, total: int) -> "WilsonInterval":
        if total <= 0:
            raise ValueError("O intervalo precisa de pelo menos uma observação.")
        if not 0 <= successes <= total:
            raise ValueError("Acertos fora da faixa de 0 até o total.")
        proportion, z_squared = successes / total, Z_95_PERCENT ** 2
        denominator = 1 + z_squared / total
        center = (proportion + z_squared / (2 * total)) / denominator
        half_width = (Z_95_PERCENT / denominator) * math.sqrt(
            proportion * (1 - proportion) / total + z_squared / (4 * total ** 2))
        return cls(successes, total, max(0.0, center - half_width), min(1.0, center + half_width))

    @property
    def proportion(self) -> float:
        return self.successes / self.total

    def describe(self) -> str:
        return (f"{self.proportion:.1%} ({self.successes}/{self.total}; "
                f"IC 95%: {self.lower:.1%} a {self.upper:.1%})")
