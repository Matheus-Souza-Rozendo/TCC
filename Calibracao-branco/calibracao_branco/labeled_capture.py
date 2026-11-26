"""Fotos rotuladas do dataset próprio: cada tomate tem um número e todas as suas fotos os mesmos rótulos.

O número do tomate existe para a divisão train/val/test ser feita por tomate:
fotos do mesmo tomate em conjuntos diferentes vazariam informação para o teste.
"""

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, FrozenSet, List, Optional

import cv2
import numpy as np

from .errors import CalibrationError

DEFECTS = ("rachado", "podre", "dano_mecanico", "mancha")
MATURITIES = ("imaturo", "intermediario", "maduro")
JPEG_QUALITY = 95
CSV_DELIMITER = ";"  # o Excel em português abre direto com ";"
CSV_COLUMNS = ["arquivo", "tomate", "foto", "data_hora", *DEFECTS, "sadio", "maturacao", "diametro_paquimetro_mm"]


@dataclass(frozen=True)
class TomatoLabels:
    tomato_id: int
    defects: FrozenSet[str]
    maturity: Optional[str]
    caliper_diameter_mm: Optional[float]

    def is_healthy(self) -> bool:
        """Sadio = nenhum defeito. Não é um rótulo marcado à parte, para não contradizer os defeitos."""
        return not self.defects


def parse_optional_diameter(text: str) -> Optional[float]:
    if not text.strip():
        return None
    try:
        value = float(text.strip().replace(",", "."))
    except ValueError:
        raise ValueError(f"Diâmetro inválido: '{text.strip()}'. Use um número em mm, ex.: 24,5.") from None
    if not 5 <= value <= 80:
        raise ValueError("Diâmetro fora da faixa esperada para tomate (5 a 80 mm).")
    return value


@dataclass(frozen=True)
class LabeledPhoto:
    path: Path
    tomato_id: int
    maturity: Optional[str]
    healthy: bool


def _no_subfolder(labels: TomatoLabels) -> str:
    return ""


class LabeledPhotoStore:
    """Grava as fotos em <pasta>/fotos/<subpasta>/ e uma linha por foto em <pasta>/rotulos.csv.

    A subpasta vem de uma regra (ex.: a maturação), para as fotos já ficarem separadas por classe.
    """

    def __init__(self, root: Path, subfolder_rule: Callable[[TomatoLabels], str] = _no_subfolder):
        self._photos_folder = root / "fotos"
        self._labels_file = root / "rotulos.csv"
        self._subfolder_rule = subfolder_rule

    def labeled_photos(self) -> List[LabeledPhoto]:
        return [
            LabeledPhoto(
                path=self._photos_folder / row["arquivo"],
                tomato_id=int(row["tomate"]),
                maturity=row["maturacao"] or None,
                healthy=row["sadio"] == "1",
            )
            for row in self._read_rows()
        ]

    def next_tomato_id(self) -> int:
        tomato_ids = [int(row["tomate"]) for row in self._read_rows()]
        return max(tomato_ids, default=0) + 1

    def photo_count(self, tomato_id: int) -> int:
        return sum(1 for row in self._read_rows() if int(row["tomate"]) == tomato_id)

    def save(self, frame: np.ndarray, labels: TomatoLabels) -> Path:
        photo_number = self.photo_count(labels.tomato_id) + 1
        relative_path = Path(self._subfolder_rule(labels)) / f"tomate_{labels.tomato_id:04d}_foto_{photo_number:02d}.jpg"
        _write_jpeg(frame, self._photos_folder / relative_path)
        self._append_row(_csv_row(relative_path.as_posix(), labels, photo_number))
        return self._photos_folder / relative_path

    def _read_rows(self) -> List[dict]:
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


def _csv_row(relative_path: str, labels: TomatoLabels, photo_number: int) -> dict:
    row = {
        "arquivo": relative_path,
        "tomate": labels.tomato_id,
        "foto": photo_number,
        "data_hora": datetime.now().isoformat(timespec="seconds"),
        "sadio": int(labels.is_healthy()),
        "maturacao": labels.maturity or "",
        # Vírgula decimal, para o Excel em português ler como número.
        "diametro_paquimetro_mm": "" if labels.caliper_diameter_mm is None
        else f"{labels.caliper_diameter_mm:.2f}".replace(".", ","),
    }
    row.update({defect: int(defect in labels.defects) for defect in DEFECTS})
    return row


def _write_jpeg(frame: np.ndarray, destination: Path) -> None:
    encoded_successfully, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not encoded_successfully:
        raise CalibrationError(f"Não foi possível gerar o JPG de '{destination.name}'.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(encoded.tobytes())
