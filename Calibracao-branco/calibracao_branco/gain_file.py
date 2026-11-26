from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np

from .channels import ChannelValues
from .errors import GainFileFormatError
from .region import RegionOfInterest
from .sampling import WhiteReferenceSample

GAIN_KEYS = {"red": "ganho_r", "green": "ganho_g", "blue": "ganho_b"}


@dataclass(frozen=True)
class CalibrationResult:
    gains: ChannelValues
    sample: WhiteReferenceSample
    region: RegionOfInterest
    strategy_name: str
    created_at: datetime


class GainFileWriter:
    """Grava o arquivo .gain: texto 'chave=valor', fácil de ler em qualquer linguagem."""

    def write(self, result: CalibrationResult, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("\n".join(_format_lines(result)) + "\n", encoding="utf-8")


class GainFileReader:
    def read_gains(self, source: Path) -> ChannelValues:
        entries = _parse_entries(source.read_text(encoding="utf-8"))
        missing_keys = [key for key in GAIN_KEYS.values() if key not in entries]
        if missing_keys:
            raise GainFileFormatError(f"Arquivo '{source}' sem as chaves: {', '.join(missing_keys)}.")
        return ChannelValues(
            red=float(entries[GAIN_KEYS["red"]]),
            green=float(entries[GAIN_KEYS["green"]]),
            blue=float(entries[GAIN_KEYS["blue"]]),
        )


def apply_gains(bgr_frame: np.ndarray, gains: ChannelValues) -> np.ndarray:
    corrected = bgr_frame.astype(np.float32) * gains.to_bgr_array().astype(np.float32)
    return np.clip(corrected, 0, 255).astype(np.uint8)


def _format_lines(result: CalibrationResult) -> List[str]:
    means = result.sample.channel_means
    variation = result.sample.channel_variation
    lines = [
        "# Ganhos de balanço de branco por canal",
        "# Como aplicar: canal_corrigido = min(255, canal_original * ganho)",
        "# Atenção: o OpenCV guarda a imagem em BGR; os nomes abaixo já indicam o canal.",
        f"data={result.created_at.isoformat(timespec='seconds')}",
        f"estrategia={result.strategy_name}",
        f"quadros_media={result.sample.frames_averaged}",
        f"regiao_gabarito={result.region.to_text()}",
        f"media_r={means.red:.3f}",
        f"media_g={means.green:.3f}",
        f"media_b={means.blue:.3f}",
        f"variacao_r={variation.red:.4f}",
        f"variacao_g={variation.green:.4f}",
        f"variacao_b={variation.blue:.4f}",
        f"{GAIN_KEYS['red']}={result.gains.red:.6f}",
        f"{GAIN_KEYS['green']}={result.gains.green:.6f}",
        f"{GAIN_KEYS['blue']}={result.gains.blue:.6f}",
    ]
    lines += [f"# AVISO: {warning}" for warning in result.sample.warnings]
    return lines


def _parse_entries(text: str) -> Dict[str, str]:
    entries = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator:
            raise GainFileFormatError(f"Linha inválida no arquivo de ganho: '{line}'.")
        entries[key.strip()] = value.strip()
    return entries
