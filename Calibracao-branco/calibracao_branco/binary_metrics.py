"""Métricas da classificação sadio x com defeito ("positivo" = com defeito, o que a bancada precisa achar)."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class BinaryMetrics:
    true_negatives: int   # sadio classificado como sadio
    false_positives: int  # sadio descartado como defeituoso
    false_negatives: int  # defeituoso que passou como sadio (o erro mais caro)
    true_positives: int

    @classmethod
    def from_labels(cls, labels: np.ndarray, predicted: np.ndarray) -> "BinaryMetrics":
        labels, predicted = np.asarray(labels).astype(bool), np.asarray(predicted).astype(bool)
        return cls(int((~labels & ~predicted).sum()), int((~labels & predicted).sum()),
                   int((labels & ~predicted).sum()), int((labels & predicted).sum()))

    @property
    def total(self) -> int:
        return self.true_negatives + self.false_positives + self.false_negatives + self.true_positives

    def accuracy(self) -> float:
        return _ratio(self.true_negatives + self.true_positives, self.total)

    def recall(self) -> float:
        """Dos defeituosos, quantos a CNN achou (sensibilidade)."""
        return _ratio(self.true_positives, self.true_positives + self.false_negatives)

    def specificity(self) -> float:
        """Dos sadios, quantos a CNN deixou passar como sadios."""
        return _ratio(self.true_negatives, self.true_negatives + self.false_positives)

    def precision(self) -> float:
        return _ratio(self.true_positives, self.true_positives + self.false_positives)

    def f1(self) -> float:
        return _ratio(2 * self.precision() * self.recall(), self.precision() + self.recall())

    def balanced_accuracy(self) -> float:
        return (self.recall() + self.specificity()) / 2


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0
