"""Avaliação no lote de teste (tomates que nem a LUT nem a CNN viram): o mesmo caminho da IHM, foto a foto.

O nome "holdout" (e não "test_") evita que o pytest confunda este módulo com um arquivo de testes.
"""

from dataclasses import dataclass

import numpy as np

from .errors import NoObjectFoundError
from .labeled_capture import LabeledPhoto
from .tomato_inspection import (InspectionReport, SortingDestination, TomatoInspection, TomatoInspectionFacade,
                                destination_for_maturity)


@dataclass(frozen=True)
class HoldoutResult:
    photo: LabeledPhoto
    report: InspectionReport
    inspection: TomatoInspection

    @property
    def expected_has_defect(self) -> bool:
        return not self.photo.healthy

    def expected_destination(self) -> SortingDestination:
        if self.expected_has_defect:
            return SortingDestination.DESCARTE
        return destination_for_maturity(self.photo.maturity)

    def is_maturity_correct(self) -> bool:
        return self.inspection.maturity.label() == self.photo.maturity

    def is_defect_correct(self) -> bool:
        return self.inspection.defect.has_defect() == self.expected_has_defect

    def is_destination_correct(self) -> bool:
        return self.inspection.destination() == self.expected_destination()

    @property
    def extra_objects(self) -> int:
        """Objetos além do tomate avaliado (folha, sujeira, outro fruto): deveria ser zero no teste."""
        return len(self.report.tomatoes) - 1


class HoldoutEvaluator:
    def __init__(self, facade: TomatoInspectionFacade):
        self._facade = facade

    def evaluate(self, photo: LabeledPhoto, raw_image: np.ndarray) -> HoldoutResult:
        report = self._facade.inspect(raw_image)
        if not report.tomatoes:
            raise NoObjectFoundError(f"Nenhum tomate segmentado em {photo.path.name}.")
        # O lote de teste tem um tomate por foto; se aparecer mais de um objeto, o maior é o tomate.
        largest = max(report.tomatoes, key=lambda inspection: inspection.tomato.area_px())
        return HoldoutResult(photo, report, largest)
