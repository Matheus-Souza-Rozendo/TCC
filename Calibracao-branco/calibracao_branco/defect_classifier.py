"""CNN de defeitos na operação: lê o ONNX exportado pelo treino só com o OpenCV (sem PyTorch na bancada)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

from .errors import CalibrationError
from .tomato_crops import CROP_SIZE_PX

DEFECT_THRESHOLD = 0.5
DEFECT_OUTPUT_INDEX = 1


@dataclass(frozen=True)
class DefectVerdict:
    is_evaluated: bool
    defect_probability: float = 0.0

    def has_defect(self) -> bool:
        return self.is_evaluated and self.defect_probability >= DEFECT_THRESHOLD

    def label(self) -> str:
        if not self.is_evaluated:
            return "sem CNN"
        return "com defeito" if self.has_defect() else "sadio"

    def confidence(self) -> float:
        """Probabilidade da classe escolhida (0,5 a 1,0)."""
        return self.defect_probability if self.has_defect() else 1.0 - self.defect_probability


class DefectClassifier(Protocol):
    def classify(self, crop_bgr: np.ndarray) -> DefectVerdict: ...


class OnnxDefectClassifierAdapter:
    """Adapta o cv2.dnn à interface DefectClassifier."""

    def __init__(self, model_file: Path):
        if not model_file.is_file():
            raise CalibrationError(f"Modelo da CNN '{model_file}' não encontrado. Rode o treinar_cnn.bat antes.")
        self._network = cv2.dnn.readNetFromONNX(str(model_file))

    def classify(self, crop_bgr: np.ndarray) -> DefectVerdict:
        # Mesma entrada do treino: RGB em 0..1, 224x224. A normalização está dentro do ONNX.
        blob = cv2.dnn.blobFromImage(crop_bgr, scalefactor=1 / 255.0, size=(CROP_SIZE_PX, CROP_SIZE_PX), swapRB=True)
        self._network.setInput(blob)
        probabilities = self._network.forward().reshape(-1)
        return DefectVerdict(True, float(probabilities[DEFECT_OUTPUT_INDEX]))


class MissingModelDefectClassifierNullObject:
    """Sem modelo treinado a IHM continua medindo cor e tamanho; o defeito aparece como "sem CNN"."""

    def classify(self, crop_bgr: np.ndarray) -> DefectVerdict:
        return DefectVerdict(False)


def defect_classifier_for(model_file: Path) -> DefectClassifier:
    if model_file.is_file():
        return OnnxDefectClassifierAdapter(model_file)
    return MissingModelDefectClassifierNullObject()
