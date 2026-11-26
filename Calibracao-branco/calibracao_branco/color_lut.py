"""MLP de cor de pixel e a LUT gerada a partir dela.

Por que MLP e LUT juntas: os pixels rotulados cobrem só uma parte das 16,7
milhões de cores possíveis. A MLP aprende uma fronteira suave entre as classes
e decide também as cores que não apareceram no treino. Depois ela é avaliada
uma vez em todas as cores e o resultado vira a tabela (LUT). Na operação só a
tabela é usada: uma consulta por pixel, sem rede neural.
"""

from pathlib import Path
from typing import Tuple

import cv2
import numpy as np
from sklearn.neural_network import MLPClassifier

from .color_classes import DISPLAY_COLORS, PixelClass
from .errors import CalibrationError

HIDDEN_LAYERS = (32, 32)
RANDOM_SEED = 42
LUT_SIZE = 256


def color_features(bgr_colors: np.ndarray) -> np.ndarray:
    """Cor em Lab normalizado (0..1). Separar brilho (L) de cor (a, b) ajuda a MLP a não confundir
    sombra com mudança de maturação."""
    lab = cv2.cvtColor(bgr_colors.reshape(-1, 1, 3).astype(np.uint8), cv2.COLOR_BGR2LAB).reshape(-1, 3)
    return lab.astype(np.float32) / 255.0


class PixelColorClassifier:
    def __init__(self):
        self._model = MLPClassifier(hidden_layer_sizes=HIDDEN_LAYERS, max_iter=300, early_stopping=True,
                                    random_state=RANDOM_SEED)

    def fit(self, bgr_colors: np.ndarray, classes: np.ndarray) -> "PixelColorClassifier":
        self._model.fit(color_features(bgr_colors), classes)
        return self

    def predict(self, bgr_colors: np.ndarray) -> np.ndarray:
        return self._model.predict(color_features(bgr_colors)).astype(np.uint8)


def balanced_subsample(colors: np.ndarray, classes: np.ndarray, per_class: int) -> Tuple[np.ndarray, np.ndarray]:
    """Até 'per_class' pixels de cada classe: sem isso, a classe com mais pixels (ex.: vermelho) domina a MLP."""
    random = np.random.default_rng(RANDOM_SEED)
    chosen = []
    for pixel_class in np.unique(classes):
        indexes = np.flatnonzero(classes == pixel_class)
        chosen.append(random.choice(indexes, size=min(per_class, len(indexes)), replace=False))
    chosen = np.concatenate(chosen)
    return colors[chosen], classes[chosen]


def build_lut(classifier: PixelColorClassifier) -> np.ndarray:
    """Tabela [azul, verde, vermelho] -> classe, para todas as 256³ cores."""
    lut = np.empty((LUT_SIZE, LUT_SIZE, LUT_SIZE), np.uint8)
    green, red = np.meshgrid(np.arange(LUT_SIZE), np.arange(LUT_SIZE), indexing="ij")
    for blue in range(LUT_SIZE):
        # Uma "fatia" de azul por vez: 65 mil cores, para não estourar a memória.
        colors = np.stack([np.full(green.size, blue), green.ravel(), red.ravel()], axis=1).astype(np.uint8)
        lut[blue] = classifier.predict(colors).reshape(LUT_SIZE, LUT_SIZE)
    return lut


def save_lut(lut: np.ndarray, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    class_names = np.array([pixel_class.label for pixel_class in PixelClass])
    with destination.open("wb") as file:
        np.savez_compressed(file, lut=lut, classes=class_names)


def load_lut(source: Path) -> np.ndarray:
    if not source.is_file():
        raise CalibrationError(f"LUT '{source}' não encontrada. Rode o gerar_lut.bat antes.")
    with np.load(source) as data:
        return data["lut"]


def apply_lut(lut: np.ndarray, bgr_image: np.ndarray) -> np.ndarray:
    """Classe de cada pixel da imagem: uma consulta na tabela por pixel."""
    return lut[bgr_image[..., 0], bgr_image[..., 1], bgr_image[..., 2]]


def class_map_image(class_map: np.ndarray) -> np.ndarray:
    colored = np.zeros(class_map.shape + (3,), np.uint8)
    for pixel_class, color in DISPLAY_COLORS.items():
        colored[class_map == pixel_class] = color
    return colored
