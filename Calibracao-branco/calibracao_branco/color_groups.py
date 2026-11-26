"""Agrupamento dos pixels do tomate por cor (k-means) e o nome que o operador dá a cada grupo.

O k-means é feito no espaço Lab porque nele a distância entre cores segue
melhor a diferença que o olho percebe do que no RGB.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

import cv2
import numpy as np

from .color_classes import PixelClass
from .color_samples import SegmentedPhoto
from .drawing import draw_text_block
from .errors import CalibrationError

DISCARD = "descartar"
NAME_CHOICES = {"1": PixelClass.VERDE.label, "2": PixelClass.AMARELADO.label, "3": PixelClass.ROSADO.label,
                "4": PixelClass.VERMELHO.label, "5": PixelClass.CALICE.label, "0": DISCARD}
KMEANS_ATTEMPTS = 5
KMEANS_CRITERIA = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
RANDOM_SEED = 42
PANEL_TILE_SIZE = 160


def to_lab(bgr_colors: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(bgr_colors.reshape(-1, 1, 3).astype(np.uint8), cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)


@dataclass(frozen=True)
class ColorGroups:
    centers_lab: np.ndarray   # (k, 3), Lab do OpenCV (0..255)
    shares: np.ndarray        # fração dos pixels de treino em cada grupo
    names: List[str]          # um nome por grupo: classe de pixel ou "descartar"

    def assign(self, bgr_colors: np.ndarray) -> np.ndarray:
        """Grupo mais próximo de cada cor."""
        lab = to_lab(bgr_colors)
        distances = np.linalg.norm(lab[:, None, :] - self.centers_lab[None, :, :], axis=2)
        return distances.argmin(axis=1)

    def mean_bgr(self, group: int) -> tuple:
        lab = self.centers_lab[group].reshape(1, 1, 3).astype(np.uint8)
        return tuple(int(value) for value in cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)[0, 0])

    def with_names(self, names: List[str]) -> "ColorGroups":
        return ColorGroups(self.centers_lab, self.shares, names)

    def save(self, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = {"centros_lab": self.centers_lab.tolist(), "fracoes": self.shares.tolist(), "nomes": self.names}
        destination.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, source: Path) -> "ColorGroups":
        data = json.loads(source.read_text(encoding="utf-8"))
        if len(data["nomes"]) != len(data["centros_lab"]):
            raise CalibrationError(f"'{source}' está incompleto: rode de novo com --reagrupar.")
        return cls(np.array(data["centros_lab"], np.float32), np.array(data["fracoes"]), data["nomes"])


def cluster_colors(bgr_colors: np.ndarray, group_count: int) -> ColorGroups:
    cv2.setRNGSeed(RANDOM_SEED)
    _, labels, centers = cv2.kmeans(to_lab(bgr_colors), group_count, None, KMEANS_CRITERIA,
                                    KMEANS_ATTEMPTS, cv2.KMEANS_PP_CENTERS)
    # Ordena do mais verde para o mais vermelho (eixo a* do Lab), para os números serem previsíveis.
    order = np.argsort(centers[:, 1])
    shares = np.bincount(labels.ravel(), minlength=group_count) / len(labels)
    return ColorGroups(centers[order], shares[order], [""] * group_count)


def group_panel(groups: ColorGroups, examples: List[SegmentedPhoto]) -> np.ndarray:
    """Uma linha por grupo: número, amostra da cor, % dos pixels e o tomate onde o grupo mais aparece,
    com só os pixels daquele grupo acesos."""
    crops = [_crop_to_mask(example) for example in examples]
    crop_groups = [groups.assign(crop.reshape(-1, 3)).reshape(crop.shape[:2]) for crop, _ in crops]
    rows = []
    for group in range(len(groups.centers_lab)):
        best = int(np.argmax([((assigned == group) & (mask > 0)).mean() for (_, mask), assigned
                              in zip(crops, crop_groups)]))
        (crop, mask), assigned = crops[best], crop_groups[best]
        rows.append(_panel_row(groups, group, _highlight(crop, (assigned == group) & (mask > 0))))
    return np.vstack(rows)


def _panel_row(groups: ColorGroups, group: int, example: np.ndarray) -> np.ndarray:
    swatch = np.full((PANEL_TILE_SIZE, PANEL_TILE_SIZE, 3), groups.mean_bgr(group), np.uint8)
    label = np.full((PANEL_TILE_SIZE, 260, 3), 255, np.uint8)
    row = np.hstack([label, swatch, cv2.resize(example, (PANEL_TILE_SIZE,) * 2, interpolation=cv2.INTER_AREA)])
    draw_text_block(row, [f"Grupo {group + 1}", f"{groups.shares[group]:.0%} dos pixels"], (5, 40))
    return row


def _highlight(crop: np.ndarray, selected: np.ndarray) -> np.ndarray:
    highlighted = (crop * 0.15).astype(np.uint8)
    highlighted[selected] = crop[selected]
    return highlighted


def _crop_to_mask(example: SegmentedPhoto):
    x, y, width, height = cv2.boundingRect(example.tomato_mask)
    return example.image[y:y + height, x:x + width], example.tomato_mask[y:y + height, x:x + width]
