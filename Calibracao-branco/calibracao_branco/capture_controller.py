"""Regras da captura, sem nada de interface: a janela só repassa os cliques para cá.

Trava: depois da primeira foto de um tomate, destino e rótulos ficam fixos até
"Novo tomate". Assim todas as fotos do mesmo tomate têm os mesmos rótulos.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet, Optional

import numpy as np

from .capture_destinations import ALL_DESTINATIONS, CaptureDestinationStrategy, store_for
from .labeled_capture import LabeledPhotoStore, TomatoLabels, parse_optional_diameter


@dataclass(frozen=True)
class LabelChoice:
    """O que está marcado no formulário no momento do clique."""

    defects: FrozenSet[str]
    maturity: Optional[str]
    diameter_text: str


class CaptureController:
    def __init__(self, datasets_root: Path):
        self._datasets_root = datasets_root
        self._destination = ALL_DESTINATIONS[0]
        self._locked_labels: Optional[TomatoLabels] = None
        self.photos_of_tomato = 0
        self.tomato_id = self._store().next_tomato_id()

    @property
    def destination(self) -> CaptureDestinationStrategy:
        return self._destination

    @property
    def is_locked(self) -> bool:
        return self._locked_labels is not None

    def dataset_folder(self) -> Path:
        return self._datasets_root / self._destination.folder_name

    def select_destination(self, destination: CaptureDestinationStrategy) -> None:
        if self.is_locked:
            raise ValueError("Termine este tomate (Novo tomate) antes de trocar o destino.")
        self._destination = destination
        self.tomato_id = self._store().next_tomato_id()

    def start_new_tomato(self) -> None:
        self._locked_labels = None
        self.photos_of_tomato = 0
        self.tomato_id = self._store().next_tomato_id()

    def take_photo(self, frame: np.ndarray, choice: LabelChoice) -> Path:
        labels = self._locked_labels or self._labels_from(choice)
        saved = self._store().save(frame, labels)
        self._locked_labels = labels
        self.photos_of_tomato += 1
        return saved

    def _labels_from(self, choice: LabelChoice) -> TomatoLabels:
        if self._destination.requires_maturity and choice.maturity is None:
            raise ValueError(f"O destino {self._destination.title} exige a maturação. Escolha uma antes da foto.")
        return TomatoLabels(self.tomato_id, choice.defects, choice.maturity,
                            parse_optional_diameter(choice.diameter_text))

    def _store(self) -> LabeledPhotoStore:
        return store_for(self._destination, self._datasets_root)
