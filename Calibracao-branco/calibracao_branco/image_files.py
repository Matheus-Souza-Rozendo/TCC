from pathlib import Path

import cv2
import numpy as np

from .errors import CalibrationError


def save_image(image: np.ndarray, destination: Path) -> None:
    # cv2.imwrite falha em silêncio com acentos no caminho no Windows;
    # codificar em memória e gravar pelo Python evita isso.
    encoded_successfully, encoded = cv2.imencode(destination.suffix or ".png", image)
    if not encoded_successfully:
        raise CalibrationError(f"Formato de imagem não suportado: '{destination.suffix}'. Use .png ou .jpg.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(encoded.tobytes())


def load_image(source: Path) -> np.ndarray:
    # Mesmo motivo do save_image: cv2.imread não abre caminhos com acento no Windows.
    if not source.is_file():
        raise CalibrationError(f"Imagem '{source}' não encontrada.")
    image = cv2.imdecode(np.fromfile(str(source), dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise CalibrationError(f"'{source}' não é uma imagem que o OpenCV consiga abrir.")
    return image
