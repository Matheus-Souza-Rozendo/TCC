"""Seção de escala pixel -> mm dentro do arquivo .gain."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .calibration_sections import SCALE_REGION_KEY, CalibrationFileSections, read_sections, write_sections
from .chessboard import ChessboardPattern
from .errors import CalibrationFileFormatError
from .key_value_file import read_entries, require_entry
from .pixel_scale import CellScale, GridCell, GridSize, PixelScaleMap, RegionGrid
from .region import RegionOfInterest

ERROR_TOLERANCE_MM = 0.5  # RF05: erro da calibração <= 0,5 mm em todas as regiões


@dataclass(frozen=True)
class ScaleCalibrationResult:
    scale_map: PixelScaleMap
    pattern: ChessboardPattern
    created_at: datetime


class ScaleSectionWriter:
    def write(self, result: ScaleCalibrationResult, gain_file: Path) -> None:
        """Troca só a seção de escala; a seção de branco fica como está."""
        white_balance_lines = read_sections(gain_file).white_balance_lines
        if not white_balance_lines:
            raise CalibrationFileFormatError(
                f"'{gain_file}' não tem a calibração de branco. Rode o calibrar.bat antes."
            )
        write_sections(CalibrationFileSections(white_balance_lines, _format_lines(result)), gain_file)


class ScaleSectionReader:
    def read(self, gain_file: Path) -> PixelScaleMap:
        entries = read_entries(gain_file)
        grid = RegionGrid(
            RegionOfInterest.from_text(require_entry(entries, SCALE_REGION_KEY)),
            GridSize.from_text(require_entry(entries, "escala_grade")),
        )
        return PixelScaleMap(grid, [_read_cell_scale(entries, cell) for cell in grid.cells()])


def tolerance_warnings(scale_map: PixelScaleMap) -> List[str]:
    return [
        f"célula {cell_scale.cell.label()} com erro máximo de {cell_scale.max_error_mm:.3f} mm "
        f"(acima de {ERROR_TOLERANCE_MM} mm do RF05)"
        for cell_scale in scale_map.cells_above_tolerance(ERROR_TOLERANCE_MM)
    ]


def _read_cell_scale(entries: Dict[str, str], cell: GridCell) -> CellScale:
    prefix = f"celula_{cell.label()}"
    return CellScale(
        cell=cell,
        mm_per_pixel=float(require_entry(entries, f"{prefix}_mm_por_pixel")),
        segment_count=int(require_entry(entries, f"{prefix}_trechos")),
        max_error_mm=float(require_entry(entries, f"{prefix}_erro_max_mm")),
        mean_error_mm=float(require_entry(entries, f"{prefix}_erro_medio_mm")),
    )


def _format_lines(result: ScaleCalibrationResult) -> List[str]:
    scale_map, pattern = result.scale_map, result.pattern
    lines = [
        "# Como usar: tamanho_mm = tamanho_px * mm_por_pixel da célula onde o objeto está",
        "# Células: celula_<linha>_<coluna>, contando a partir de 0 no canto superior esquerdo",
        f"escala_data={result.created_at.isoformat(timespec='seconds')}",
        f"{SCALE_REGION_KEY}={scale_map.grid.region.to_text()}",
        f"escala_grade={scale_map.grid.size.to_text()}",
        f"escala_tabuleiro_cantos_internos={pattern.inner_columns}x{pattern.inner_rows}",
        f"escala_tamanho_quadrado_mm={pattern.square_size_mm:.3f}",
        f"escala_mm_por_pixel_medio={scale_map.mean_mm_per_pixel():.6f}",
        f"escala_erro_max_mm={scale_map.max_error_mm():.4f}",
        f"escala_tolerancia_mm={ERROR_TOLERANCE_MM}",
    ]
    for cell_scale in scale_map.cell_scales:
        prefix = f"celula_{cell_scale.cell.label()}"
        lines += [
            f"{prefix}_regiao={cell_scale.cell.region.to_text()}",
            f"{prefix}_mm_por_pixel={cell_scale.mm_per_pixel:.6f}",
            f"{prefix}_trechos={cell_scale.segment_count}",
            f"{prefix}_erro_max_mm={cell_scale.max_error_mm:.4f}",
            f"{prefix}_erro_medio_mm={cell_scale.mean_error_mm:.4f}",
        ]
    lines += [f"# AVISO: {warning}" for warning in tolerance_warnings(scale_map)]
    return lines
