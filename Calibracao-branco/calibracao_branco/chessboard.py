from dataclasses import dataclass
from typing import Tuple

import cv2
import numpy as np

from .dimensions import parse_columns_by_rows
from .errors import ChessboardNotFoundError

SUBPIXEL_SEARCH_WINDOW = (11, 11)
SUBPIXEL_STOP_CRITERIA = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)


@dataclass(frozen=True)
class ChessboardPattern:
    """Tabuleiro impresso. 'Cantos internos' são os encontros de 4 quadrados:
    um tabuleiro de 10 x 7 quadrados tem 9 x 6 cantos internos."""

    inner_columns: int
    inner_rows: int
    square_size_mm: float

    def __post_init__(self):
        if self.inner_columns < 2 or self.inner_rows < 2:
            raise ValueError("O tabuleiro precisa ter pelo menos 2 x 2 cantos internos.")
        if self.square_size_mm <= 0:
            raise ValueError("O tamanho do quadrado precisa ser maior que zero.")

    @classmethod
    def from_text(cls, inner_corners_text: str, square_size_mm: float) -> "ChessboardPattern":
        """Lê os cantos internos no formato 'colunas x linhas' (ex.: 9x6)."""
        columns, rows = parse_columns_by_rows(inner_corners_text)
        return cls(inner_columns=columns, inner_rows=rows, square_size_mm=square_size_mm)

    def opencv_size(self) -> Tuple[int, int]:
        return self.inner_columns, self.inner_rows


class ChessboardDetector:
    """Encontra os cantos internos com precisão subpixel.

    Tenta primeiro o detector 'SB' (mais preciso e tolerante à iluminação) e,
    se falhar, o detector clássico, que às vezes resolve tabuleiros com reflexo.
    """

    def __init__(self, pattern: ChessboardPattern):
        self._pattern = pattern

    def detect(self, frame: np.ndarray) -> np.ndarray:
        """Devolve os cantos como matriz (linhas, colunas, 2) em pixels (x, y)."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        found, corners = cv2.findChessboardCornersSB(
            gray, self._pattern.opencv_size(), flags=cv2.CALIB_CB_EXHAUSTIVE | cv2.CALIB_CB_ACCURACY
        )
        if not found:
            corners = self._detect_with_classic_method(gray)
        return corners.reshape(self._pattern.inner_rows, self._pattern.inner_columns, 2)

    def _detect_with_classic_method(self, gray: np.ndarray) -> np.ndarray:
        found, corners = cv2.findChessboardCorners(
            gray, self._pattern.opencv_size(), flags=cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE
        )
        if not found:
            raise ChessboardNotFoundError(
                f"Tabuleiro de {self._pattern.inner_columns}x{self._pattern.inner_rows} cantos internos não encontrado.\n"
                "  - Conte os cantos INTERNOS (encontro de 4 quadrados), não os quadrados.\n"
                "  - O tabuleiro inteiro precisa aparecer na imagem, plano e sem reflexo."
            )
        return cv2.cornerSubPix(gray, corners, SUBPIXEL_SEARCH_WINDOW, (-1, -1), SUBPIXEL_STOP_CRITERIA)

