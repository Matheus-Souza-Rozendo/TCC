"""Escala pixel -> mm por região, medida com os cantos de um tabuleiro de xadrez.

Cada par de cantos vizinhos do tabuleiro está a exatamente 1 quadrado de
distância. Medindo esse trecho em pixels em vários pontos da imagem, dá para
saber quantos mm vale 1 pixel em cada parte da região de interesse. Isso
compensa a distorção da lente, que faz o mesmo objeto parecer menor nas bordas.
"""

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from .dimensions import format_columns_by_rows, parse_columns_by_rows
from .errors import IncompleteRegionCoverageError
from .region import RegionOfInterest

MINIMUM_SEGMENTS_PER_CELL = 4


@dataclass(frozen=True)
class GridSize:
    columns: int
    rows: int

    def __post_init__(self):
        if self.columns < 1 or self.rows < 1:
            raise ValueError("A grade precisa ter pelo menos 1 coluna e 1 linha.")

    @classmethod
    def from_text(cls, text: str) -> "GridSize":
        columns, rows = parse_columns_by_rows(text)
        return cls(columns=columns, rows=rows)

    def to_text(self) -> str:
        return format_columns_by_rows(self.columns, self.rows)


@dataclass(frozen=True)
class GridCell:
    row: int
    column: int
    region: RegionOfInterest

    def label(self) -> str:
        return f"{self.row}_{self.column}"


class RegionGrid:
    """Divide a região de interesse em células que cobrem tudo, sem sobra e sem sobreposição."""

    def __init__(self, region: RegionOfInterest, size: GridSize):
        if size.columns > region.width or size.rows > region.height:
            raise ValueError(f"A grade {size.to_text()} é maior que a região {region.to_text()} em pixels.")
        self.region = region
        self.size = size

    def cells(self) -> List[GridCell]:
        column_edges = _split_evenly(self.region.x, self.region.width, self.size.columns)
        row_edges = _split_evenly(self.region.y, self.region.height, self.size.rows)
        return [
            GridCell(row, column, RegionOfInterest(
                x=column_edges[column], y=row_edges[row],
                width=column_edges[column + 1] - column_edges[column],
                height=row_edges[row + 1] - row_edges[row],
            ))
            for row in range(self.size.rows)
            for column in range(self.size.columns)
        ]


@dataclass(frozen=True)
class CornerSegment:
    """Trecho entre dois cantos vizinhos do tabuleiro: mede 1 quadrado no mundo real."""

    start: np.ndarray
    end: np.ndarray

    def midpoint(self) -> np.ndarray:
        return (self.start + self.end) / 2

    def length_px(self) -> float:
        return float(np.linalg.norm(self.end - self.start))


@dataclass(frozen=True)
class CellScale:
    cell: GridCell
    mm_per_pixel: float
    segment_count: int
    max_error_mm: float
    mean_error_mm: float


class PixelScaleMap:
    """Tabela de mm/pixel por célula. É o que o resto do projeto usa para medir os tomates."""

    def __init__(self, grid: RegionGrid, cell_scales: List[CellScale]):
        self.grid = grid
        self.cell_scales = cell_scales

    def mm_per_pixel_at(self, x: float, y: float) -> float:
        for cell_scale in self.cell_scales:
            if cell_scale.cell.region.contains(x, y):
                return cell_scale.mm_per_pixel
        raise ValueError(f"O ponto ({x:.0f}, {y:.0f}) está fora da região calibrada {self.grid.region.to_text()}.")

    def mean_mm_per_pixel(self) -> float:
        return float(np.mean([cell_scale.mm_per_pixel for cell_scale in self.cell_scales]))

    def max_error_mm(self) -> float:
        return max(cell_scale.max_error_mm for cell_scale in self.cell_scales)

    def cells_above_tolerance(self, tolerance_mm: float) -> List[CellScale]:
        return [cell_scale for cell_scale in self.cell_scales if cell_scale.max_error_mm > tolerance_mm]


class PixelScaleCalibrator:
    def __init__(self, square_size_mm: float, grid: RegionGrid):
        self._square_size_mm = square_size_mm
        self._grid = grid

    def calibrate(self, corners: np.ndarray) -> PixelScaleMap:
        """'corners' é a matriz (linhas, colunas, 2) devolvida pelo ChessboardDetector."""
        segments = segments_between_neighbors(corners)
        segments_by_cell = [(cell, _segments_inside(cell, segments)) for cell in self._grid.cells()]
        _ensure_every_cell_is_covered(segments_by_cell)
        return PixelScaleMap(self._grid, [self._scale_of(cell, cell_segments) for cell, cell_segments in segments_by_cell])

    def _scale_of(self, cell: GridCell, segments: List[CornerSegment]) -> CellScale:
        lengths_px = np.array([segment.length_px() for segment in segments])
        mm_per_pixel = float(np.mean(self._square_size_mm / lengths_px))
        errors_mm = np.abs(lengths_px * mm_per_pixel - self._square_size_mm)
        return CellScale(cell, mm_per_pixel, len(segments), float(errors_mm.max()), float(errors_mm.mean()))


def segments_between_neighbors(corners: np.ndarray) -> List[CornerSegment]:
    rows, columns = corners.shape[:2]
    horizontal = [CornerSegment(corners[row, column], corners[row, column + 1])
                  for row in range(rows) for column in range(columns - 1)]
    vertical = [CornerSegment(corners[row, column], corners[row + 1, column])
                for row in range(rows - 1) for column in range(columns)]
    return horizontal + vertical


def _segments_inside(cell: GridCell, segments: List[CornerSegment]) -> List[CornerSegment]:
    return [segment for segment in segments if cell.region.contains(*segment.midpoint())]


def _ensure_every_cell_is_covered(segments_by_cell: List[Tuple[GridCell, List[CornerSegment]]]) -> None:
    uncovered = [cell.label() for cell, cell_segments in segments_by_cell
                 if len(cell_segments) < MINIMUM_SEGMENTS_PER_CELL]
    if uncovered:
        raise IncompleteRegionCoverageError(
            f"As células {', '.join(uncovered)} (linha_coluna) têm menos de {MINIMUM_SEGMENTS_PER_CELL} "
            "trechos do tabuleiro.\n"
            "  - O tabuleiro precisa cobrir TODA a região marcada, com sobra nas bordas.\n"
            "  - Use um tabuleiro com quadrados menores ou uma grade com menos células (ex.: 2x2)."
        )


def _split_evenly(start: int, length: int, parts: int) -> List[int]:
    return [start + round(index * length / parts) for index in range(parts + 1)]
