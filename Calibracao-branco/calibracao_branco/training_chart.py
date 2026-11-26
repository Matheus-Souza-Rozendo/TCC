"""Curva de aprendizado desenhada com o OpenCV (sem depender do matplotlib na bancada)."""

from typing import List, Sequence, Tuple

import cv2
import numpy as np

WIDTH, HEIGHT = 900, 420
MARGIN_LEFT, MARGIN_RIGHT, MARGIN_TOP, MARGIN_BOTTOM = 60, 20, 40, 50
TRAIN_COLOR = (200, 120, 30)
VALIDATION_COLOR = (40, 40, 220)
ACCURACY_COLOR = (40, 150, 40)
BEST_EPOCH_COLOR = (150, 150, 150)
TEXT_COLOR = (40, 40, 40)
FONT = cv2.FONT_HERSHEY_SIMPLEX


def learning_curve_image(history: Sequence, best_epoch: int) -> np.ndarray:
    """Perdas (eixo esquerdo) e acurácia balanceada da validação (0 a 100%, mesma altura)."""
    image = np.full((HEIGHT, WIDTH, 3), 255, np.uint8)
    epochs = [record.epoch for record in history]
    highest_loss = max(max(r.train_loss for r in history), max(r.validation_loss for r in history), 1e-6)
    plot = _PlotArea(len(epochs))
    _draw_axes(image, highest_loss)
    _draw_epoch_ticks(image, (plot, epochs))
    cv2.line(image, plot.point(best_epoch, 0), plot.point(best_epoch, 1), BEST_EPOCH_COLOR, 1)
    _draw_series(image, plot.points(epochs, [r.train_loss / highest_loss for r in history]), TRAIN_COLOR)
    _draw_series(image, plot.points(epochs, [r.validation_loss / highest_loss for r in history]), VALIDATION_COLOR)
    _draw_series(image, plot.points(epochs, [r.validation_balanced_accuracy for r in history]), ACCURACY_COLOR)
    _draw_legend(image, best_epoch)
    return image


class _PlotArea:
    def __init__(self, epoch_count: int):
        self._epoch_count = max(epoch_count, 2)

    def point(self, epoch: float, fraction: float) -> Tuple[int, int]:
        x = MARGIN_LEFT + (epoch - 1) / (self._epoch_count - 1) * (WIDTH - MARGIN_LEFT - MARGIN_RIGHT)
        y = HEIGHT - MARGIN_BOTTOM - fraction * (HEIGHT - MARGIN_TOP - MARGIN_BOTTOM)
        return round(x), round(y)

    def points(self, epochs: List[int], fractions: List[float]) -> np.ndarray:
        return np.array([self.point(e, f) for e, f in zip(epochs, fractions)], np.int32)


def _draw_axes(image: np.ndarray, highest_loss: float) -> None:
    bottom, right = HEIGHT - MARGIN_BOTTOM, WIDTH - MARGIN_RIGHT
    cv2.line(image, (MARGIN_LEFT, MARGIN_TOP), (MARGIN_LEFT, bottom), TEXT_COLOR, 1)
    cv2.line(image, (MARGIN_LEFT, bottom), (right, bottom), TEXT_COLOR, 1)
    for step in range(5):
        y = round(bottom - step / 4 * (bottom - MARGIN_TOP))
        cv2.line(image, (MARGIN_LEFT, y), (right, y), (230, 230, 230), 1)
        cv2.putText(image, f"{step * 25}%", (8, y + 4), FONT, 0.4, ACCURACY_COLOR, 1, cv2.LINE_AA)
    cv2.putText(image, f"perda max. {highest_loss:.2f}", (MARGIN_LEFT, HEIGHT - 8), FONT, 0.45,
                TEXT_COLOR, 1, cv2.LINE_AA)
    cv2.putText(image, "epoca", (WIDTH // 2 - 20, HEIGHT - 8), FONT, 0.5, TEXT_COLOR, 1, cv2.LINE_AA)


def _draw_epoch_ticks(image: np.ndarray, plot_and_epochs) -> None:
    plot, epochs = plot_and_epochs
    for epoch in epochs:
        if epoch == 1 or epoch % 5 == 0:
            x, y = plot.point(epoch, 0)
            cv2.line(image, (x, y), (x, y + 5), TEXT_COLOR, 1)
            cv2.putText(image, str(epoch), (x - 6, y + 20), FONT, 0.4, TEXT_COLOR, 1, cv2.LINE_AA)


def _draw_series(image: np.ndarray, points: np.ndarray, color: Tuple[int, int, int]) -> None:
    cv2.polylines(image, [points], False, color, 2, cv2.LINE_AA)


def _draw_legend(image: np.ndarray, best_epoch: int) -> None:
    entries = [("perda treino", TRAIN_COLOR), ("perda validacao", VALIDATION_COLOR),
               ("acuracia balanceada (validacao)", ACCURACY_COLOR), (f"melhor epoca: {best_epoch}", BEST_EPOCH_COLOR)]
    x = MARGIN_LEFT + 10
    for text, color in entries:
        cv2.line(image, (x, 22), (x + 20, 22), color, 3)
        cv2.putText(image, text, (x + 25, 26), FONT, 0.45, TEXT_COLOR, 1, cv2.LINE_AA)
        x += 35 + cv2.getTextSize(text, FONT, 0.45, 1)[0][0]
