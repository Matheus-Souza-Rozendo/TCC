"""Para onde vão as fotos e o que cada destino exige (padrão Strategy).

Cada destino define a pasta do dataset, a subpasta de cada foto (separada por
classe, para já sair no formato que as bibliotecas de treino leem) e quais
rótulos são obrigatórios.
"""

from pathlib import Path
from typing import List, Protocol

from .labeled_capture import LabeledPhotoStore, TomatoLabels


class CaptureDestinationStrategy(Protocol):
    title: str
    folder_name: str
    requires_maturity: bool

    def subfolder(self, labels: TomatoLabels) -> str: ...


class ColorDestinationStrategy:
    """Fotos para a LUT de cor: a maturação é obrigatória e define a subpasta."""

    title = "Cor (LUT)"
    folder_name = "Dataset-cor"
    requires_maturity = True

    def subfolder(self, labels: TomatoLabels) -> str:
        return labels.maturity


class DefectDestinationStrategy:
    """Fotos para a CNN: subpastas sadio/ e com_defeito/ (formato "uma pasta por classe")."""

    title = "Defeitos (CNN)"
    folder_name = "Dataset-proprio"
    requires_maturity = False

    def subfolder(self, labels: TomatoLabels) -> str:
        return "sadio" if labels.is_healthy() else "com_defeito"


class TestDestinationStrategy:
    """Teste do 2º lote: avalia cor, defeito e tamanho juntos, então não separa por classe."""

    title = "Teste (2º lote)"
    folder_name = "Dataset-teste"
    requires_maturity = True

    def subfolder(self, labels: TomatoLabels) -> str:
        return ""


ALL_DESTINATIONS: List[CaptureDestinationStrategy] = [
    ColorDestinationStrategy(), DefectDestinationStrategy(), TestDestinationStrategy(),
]


def store_for(destination: CaptureDestinationStrategy, datasets_root: Path) -> LabeledPhotoStore:
    return LabeledPhotoStore(datasets_root / destination.folder_name, destination.subfolder)
