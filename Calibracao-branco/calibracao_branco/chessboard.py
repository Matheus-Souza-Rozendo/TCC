from dataclasses import dataclass

import cv2
import numpy as np

from .dimensions import format_columns_by_rows
from .errors import ChessboardNotFoundError

# Menor tabuleiro aceito (cantos internos). Com CALIB_CB_LARGER o OpenCV procura
# a partir deste tamanho e devolve o maior tabuleiro que encontrar, então não é
# preciso informar quantos cantos o papel tem.
MINIMUM_INNER_CORNERS = (3, 3)
DETECTION_FLAGS = cv2.CALIB_CB_EXHAUSTIVE | cv2.CALIB_CB_ACCURACY | cv2.CALIB_CB_LARGER


@dataclass(frozen=True)
class ChessboardDetection:
    """Cantos internos encontrados, como matriz (linhas, colunas, 2) em pixels (x, y)."""

    corners: np.ndarray

    @property
    def rows(self) -> int:
        return self.corners.shape[0]

    @property
    def columns(self) -> int:
        return self.corners.shape[1]

    def size_text(self) -> str:
        return format_columns_by_rows(self.columns, self.rows)


class ChessboardDetector:
    """Encontra o tabuleiro sem saber o número de cantos, com precisão subpixel.

    Aceita tabuleiro cortado pela borda da imagem: só a parte visível é usada.
    """

    def detect(self, frame: np.ndarray) -> ChessboardDetection:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        found, corners, meta = cv2.findChessboardCornersSBWithMeta(gray, MINIMUM_INNER_CORNERS, DETECTION_FLAGS)
        if not found:
            raise ChessboardNotFoundError(
                "Nenhum tabuleiro de xadrez encontrado.\n"
                "  - Precisam aparecer pelo menos 4 x 4 quadrados.\n"
                "  - O papel precisa estar plano, focado e sem reflexo da luz."
            )
        rows, columns = meta.shape[:2]
        return ChessboardDetection(corners.reshape(rows, columns, 2))
