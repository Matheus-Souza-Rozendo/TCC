"""Fotos rotuladas do dataset próprio: cada tomate tem um número e todas as suas fotos os mesmos rótulos.

O número do tomate existe para a divisão train/val/test ser feita por tomate:
fotos do mesmo tomate em conjuntos diferentes vazariam informação para o teste.
"""

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import FrozenSet, Optional

import cv2
import numpy as np

from .errors import CalibrationError

DEFECT_CODES = {"r": "rachado", "p": "podre", "d": "dano_mecanico", "m": "mancha"}
MATURITY_CODES = {"1": "imaturo", "2": "intermediario", "3": "maduro"}
JPEG_QUALITY = 95
CSV_DELIMITER = ";"  # o Excel em português abre direto com ";"
CSV_COLUMNS = ["arquivo", "tomate", "foto", "data_hora", *DEFECT_CODES.values(), "sadio",
               "maturacao", "diametro_paquimetro_mm"]


@dataclass(frozen=True)
class TomatoLabels:
    tomato_id: int
    defects: FrozenSet[str]
    maturity: Optional[str]
    caliper_diameter_mm: Optional[float]

    def is_healthy(self) -> bool:
        """Sadio = nenhum defeito. Não é um rótulo marcado à parte, para não contradizer os defeitos."""
        return not self.defects

    def describe(self) -> str:
        defects = ", ".join(sorted(self.defects)) if self.defects else "sadio"
        maturity = self.maturity or "nao informada"
        diameter = f"{self.caliper_diameter_mm:.2f} mm" if self.caliper_diameter_mm is not None else "nao informado"
        return f"tomate {self.tomato_id} | defeitos: {defects} | maturacao: {maturity} | paquimetro: {diameter}"


def parse_defects(text: str) -> FrozenSet[str]:
    """Letras juntas, em qualquer ordem: 'rp' = rachado e podre. Vazio = sadio."""
    letters = set(text.strip().lower().replace(" ", "").replace(",", ""))
    unknown = letters - set(DEFECT_CODES)
    if unknown:
        raise ValueError(f"Letra(s) de defeito invalida(s): {', '.join(sorted(unknown))}. Use r, p, d, m.")
    return frozenset(DEFECT_CODES[letter] for letter in letters)


def parse_maturity(text: str) -> Optional[str]:
    code = text.strip()
    if not code:
        return None
    if code not in MATURITY_CODES:
        raise ValueError("Maturacao invalida. Use 1, 2, 3 ou ENTER para nao informar.")
    return MATURITY_CODES[code]


def parse_optional_diameter(text: str) -> Optional[float]:
    if not text.strip():
        return None
    value = float(text.strip().replace(",", "."))
    if not 5 <= value <= 80:
        raise ValueError("Diametro fora da faixa esperada para tomate (5 a 80 mm).")
    return value


class LabeledPhotoStore:
    """Grava as fotos em <pasta>/fotos/ e uma linha por foto em <pasta>/rotulos.csv."""

    def __init__(self, root: Path):
        self._photos_folder = root / "fotos"
        self._labels_file = root / "rotulos.csv"

    def next_tomato_id(self) -> int:
        tomato_ids = [int(row["tomate"]) for row in self._read_rows()]
        return max(tomato_ids, default=0) + 1

    def photo_count(self, tomato_id: int) -> int:
        return sum(1 for row in self._read_rows() if int(row["tomate"]) == tomato_id)

    def save(self, frame: np.ndarray, labels: TomatoLabels) -> Path:
        photo_number = self.photo_count(labels.tomato_id) + 1
        destination = self._photos_folder / f"tomate_{labels.tomato_id:04d}_foto_{photo_number:02d}.jpg"
        _write_jpeg(frame, destination)
        self._append_row(_csv_row(destination.name, labels, photo_number))
        return destination

    def _read_rows(self):
        if not self._labels_file.is_file():
            return []
        with self._labels_file.open(encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file, delimiter=CSV_DELIMITER))

    def _append_row(self, row: dict) -> None:
        is_new_file = not self._labels_file.is_file()
        self._labels_file.parent.mkdir(parents=True, exist_ok=True)
        # utf-8-sig: com a marca BOM o Excel reconhece os acentos.
        with self._labels_file.open("a", encoding="utf-8-sig" if is_new_file else "utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS, delimiter=CSV_DELIMITER)
            if is_new_file:
                writer.writeheader()
            writer.writerow(row)


def _csv_row(file_name: str, labels: TomatoLabels, photo_number: int) -> dict:
    row = {
        "arquivo": file_name,
        "tomate": labels.tomato_id,
        "foto": photo_number,
        "data_hora": datetime.now().isoformat(timespec="seconds"),
        "sadio": int(labels.is_healthy()),
        "maturacao": labels.maturity or "",
        # Vírgula decimal, para o Excel em português ler como número.
        "diametro_paquimetro_mm": "" if labels.caliper_diameter_mm is None
        else f"{labels.caliper_diameter_mm:.2f}".replace(".", ","),
    }
    row.update({defect: int(defect in labels.defects) for defect in DEFECT_CODES.values()})
    return row


def _write_jpeg(frame: np.ndarray, destination: Path) -> None:
    encoded_successfully, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not encoded_successfully:
        raise CalibrationError(f"Nao foi possivel gerar o JPG de '{destination.name}'.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(encoded.tobytes())
