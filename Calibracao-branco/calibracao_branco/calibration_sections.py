"""O arquivo .gain guarda duas calibrações, cada uma na sua seção:

1. balanço de branco (calibrar.bat), no começo do arquivo;
2. escala pixel -> mm (calibrar_escala.bat), depois do marcador abaixo.

Cada calibração reescreve só a sua seção e preserva a outra.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List

from .key_value_file import write_lines

SCALE_SECTION_MARKER = "# ===== Escala pixel -> mm por região ====="
SCALE_REGION_KEY = "escala_regiao_interesse"


@dataclass(frozen=True)
class CalibrationFileSections:
    white_balance_lines: List[str]
    scale_lines: List[str]


def read_sections(source: Path) -> CalibrationFileSections:
    if not source.is_file():
        return CalibrationFileSections(white_balance_lines=[], scale_lines=[])
    lines = source.read_text(encoding="utf-8").splitlines()
    if SCALE_SECTION_MARKER not in lines:
        return CalibrationFileSections(white_balance_lines=lines, scale_lines=[])
    marker_index = lines.index(SCALE_SECTION_MARKER)
    return CalibrationFileSections(white_balance_lines=lines[:marker_index], scale_lines=lines[marker_index + 1:])


def write_sections(sections: CalibrationFileSections, destination: Path) -> None:
    lines = list(sections.white_balance_lines)
    if sections.scale_lines:
        lines += [SCALE_SECTION_MARKER] + sections.scale_lines
    write_lines(lines, destination)
