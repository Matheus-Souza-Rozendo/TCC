from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

import numpy as np

from .channels import ChannelValues
from .calibration_sections import SCALE_REGION_KEY, CalibrationFileSections, read_sections, write_sections
from .key_value_file import read_entries, require_entry
from .region import RegionOfInterest
from .sampling import WhiteReferenceSample

GAIN_KEYS = {"red": "ganho_r", "green": "ganho_g", "blue": "ganho_b"}
REGION_KEY = "regiao_gabarito"
CAMERA_KEY = "camera"
DEFAULT_CAMERA_ADDRESS = "0"


@dataclass(frozen=True)
class CalibrationResult:
    gains: ChannelValues
    sample: WhiteReferenceSample
    region: RegionOfInterest
    strategy_name: str
    created_at: datetime
    camera_address: str = DEFAULT_CAMERA_ADDRESS


class GainFileWriter:
    """Grava a seção de branco do .gain: texto 'chave=valor', fácil de ler em qualquer linguagem."""

    def write(self, result: CalibrationResult, destination: Path) -> None:
        """Preserva a escala pixel -> mm só se ela foi medida na mesma região;
        com outra região, a escala antiga deixa de valer e é descartada."""
        scale_lines = read_sections(destination).scale_lines
        if not _scale_belongs_to(scale_lines, result.region):
            scale_lines = []
        write_sections(CalibrationFileSections(_format_lines(result), scale_lines), destination)


class GainFileReader:
    def read_gains(self, source: Path) -> ChannelValues:
        entries = read_entries(source)
        return ChannelValues(
            red=float(require_entry(entries, GAIN_KEYS["red"])),
            green=float(require_entry(entries, GAIN_KEYS["green"])),
            blue=float(require_entry(entries, GAIN_KEYS["blue"])),
        )

    def read_region(self, source: Path) -> RegionOfInterest:
        """Região onde o gabarito branco foi medido, reaproveitada como região de interesse."""
        return RegionOfInterest.from_text(require_entry(read_entries(source), REGION_KEY))

    def read_camera_address(self, source: Path) -> str:
        """Câmera usada na calibração de branco; arquivos antigos, sem a chave, usam a padrão."""
        return read_entries(source).get(CAMERA_KEY, DEFAULT_CAMERA_ADDRESS)


def apply_gains(bgr_frame: np.ndarray, gains: ChannelValues) -> np.ndarray:
    corrected = bgr_frame.astype(np.float32) * gains.to_bgr_array().astype(np.float32)
    return np.clip(corrected, 0, 255).astype(np.uint8)


def _scale_belongs_to(scale_lines: List[str], region: RegionOfInterest) -> bool:
    return f"{SCALE_REGION_KEY}={region.to_text()}" in scale_lines


def _format_lines(result: CalibrationResult) -> List[str]:
    means = result.sample.channel_means
    variation = result.sample.channel_variation
    lines = [
        "# Ganhos de balanço de branco por canal",
        "# Como aplicar: canal_corrigido = min(255, canal_original * ganho)",
        "# Atenção: o OpenCV guarda a imagem em BGR; os nomes abaixo já indicam o canal.",
        f"data={result.created_at.isoformat(timespec='seconds')}",
        f"{CAMERA_KEY}={result.camera_address}",
        f"estrategia={result.strategy_name}",
        f"quadros_media={result.sample.frames_averaged}",
        f"{REGION_KEY}={result.region.to_text()}",
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
