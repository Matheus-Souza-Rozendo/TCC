"""Contagem por destino e registro em CSV de cada tomate classificado (sem nada de interface)."""

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .tomato_inspection import InspectionReport, SortingDestination, TomatoInspection

CSV_DELIMITER = ";"
CSV_COLUMNS = ["data_hora", "classificacao", "tomate", "destino", "maturacao", "pct_colorido", "pct_vermelho",
               "defeito", "prob_defeito", "diametro_mm", "comprimento_mm", "largura_mm", "circularidade"]


@dataclass(frozen=True)
class InspectionRecord:
    timestamp: datetime
    round_number: int
    inspection: TomatoInspection

    def csv_row(self) -> Dict[str, str]:
        inspection = self.inspection
        return {
            "data_hora": self.timestamp.isoformat(timespec="seconds"),
            "classificacao": str(self.round_number),
            "tomate": str(inspection.number),
            "destino": inspection.destination().title,
            "maturacao": inspection.maturity.label(),
            "pct_colorido": decimal_comma(100 * inspection.maturity.surface.colored_fraction, 1),
            "pct_vermelho": decimal_comma(100 * inspection.maturity.surface.red_fraction, 1),
            "defeito": inspection.defect.label(),
            "prob_defeito": decimal_comma(inspection.defect.defect_probability, 3) if inspection.defect.is_evaluated else "",
            "diametro_mm": decimal_comma(inspection.size.diameter_mm, 2),
            "comprimento_mm": decimal_comma(inspection.size.length_mm, 2),
            "largura_mm": decimal_comma(inspection.size.width_mm, 2),
            "circularidade": decimal_comma(inspection.size.circularity, 3),
        }


def decimal_comma(value: float, decimals: int) -> str:
    """Vírgula decimal: o Excel em português lê como número."""
    return f"{value:.{decimals}f}".replace(".", ",")


class InspectionSession:
    def __init__(self, log_folder: Path):
        self._log_file = log_folder / f"inspecoes_{datetime.now():%Y-%m-%d}.csv"
        self.round_number = 0
        self.records: List[InspectionRecord] = []
        self.counts: Dict[SortingDestination, int] = {destination: 0 for destination in SortingDestination}

    @property
    def log_file(self) -> Path:
        return self._log_file

    def register(self, report: InspectionReport) -> List[InspectionRecord]:
        self.round_number += 1
        now = datetime.now()
        new_records = [InspectionRecord(now, self.round_number, inspection) for inspection in report.tomatoes]
        for record in new_records:
            self.counts[record.inspection.destination()] += 1
        self.records.extend(new_records)
        self._append_to_log(new_records)
        return new_records

    def total(self) -> int:
        return sum(self.counts.values())

    def reset_counts(self) -> None:
        """Zera só a tela; o CSV do dia continua com tudo."""
        self.records.clear()
        self.counts = {destination: 0 for destination in SortingDestination}

    def _append_to_log(self, records: List[InspectionRecord]) -> None:
        if not records:
            return
        is_new_file = not self._log_file.is_file()
        self._log_file.parent.mkdir(parents=True, exist_ok=True)
        with self._log_file.open("a", encoding="utf-8-sig" if is_new_file else "utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS, delimiter=CSV_DELIMITER)
            if is_new_file:
                writer.writeheader()
            writer.writerows(record.csv_row() for record in records)
