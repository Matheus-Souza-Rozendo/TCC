"""Formato comum dos arquivos de calibração: texto 'chave=valor', '#' para comentário."""

from pathlib import Path
from typing import Dict, List

from .errors import CalibrationFileFormatError


def read_entries(source: Path) -> Dict[str, str]:
    if not source.is_file():
        raise CalibrationFileFormatError(f"Arquivo '{source}' não encontrado.")
    entries = {}
    for line in source.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator:
            raise CalibrationFileFormatError(f"Linha inválida em '{source}': '{line}'.")
        entries[key.strip()] = value.strip()
    return entries


def require_entry(entries: Dict[str, str], key: str) -> str:
    if key not in entries:
        raise CalibrationFileFormatError(f"Chave '{key}' não encontrada no arquivo de calibração.")
    return entries[key]


def write_lines(lines: List[str], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
