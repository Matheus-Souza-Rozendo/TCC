import sys
from typing import List, Protocol, Union

import cv2
import numpy as np

from .errors import CameraUnavailableError

CameraAddress = Union[int, str]

OPEN_TIMEOUT_MS = 5000
READ_ATTEMPTS = 5


class FrameSource(Protocol):
    def read_frame(self) -> np.ndarray: ...

    def close(self) -> None: ...


class OpenCvCameraAdapter:
    """Isola o restante do sistema da API do OpenCV.

    Aceita o índice da webcam virtual do DroidCam (ex.: 1) ou a URL do
    stream por Wi-Fi (ex.: http://192.168.0.10:4747/video).
    """

    def __init__(self, address: CameraAddress):
        self._address = address
        self._capture = open_working_capture(address)

    def read_frame(self) -> np.ndarray:
        # Pelo Wi-Fi o stream perde quadros de vez em quando; uma falha isolada não é erro.
        for _ in range(READ_ATTEMPTS):
            frame_was_read, frame = self._capture.read()
            if frame_was_read:
                return frame
        raise CameraUnavailableError(
            f"A câmera '{self._address}' parou de enviar imagem. Confira a conexão do DroidCam."
        )

    def close(self) -> None:
        self._capture.release()

    def __enter__(self) -> "OpenCvCameraAdapter":
        return self

    def __exit__(self, *exception_info) -> None:
        self.close()


def average_frames(frame_source: FrameSource, frame_count: int) -> np.ndarray:
    """Média de vários quadros de uma cena parada: reduz o ruído do sensor."""
    accumulated = frame_source.read_frame().astype(np.float64)
    for _ in range(frame_count - 1):
        accumulated += frame_source.read_frame()
    return np.round(accumulated / frame_count).astype(np.uint8)


def open_working_capture(address: CameraAddress) -> cv2.VideoCapture:
    """Tenta cada backend do OpenCV e fica com o primeiro que entrega imagem de verdade.

    Abrir não basta: com o DroidCam o DirectShow às vezes abre a câmera mas só
    devolve quadros vazios, e o Media Foundation funciona (ou o contrário).
    """
    for backend in candidate_backends(address):
        capture = create_capture(address, backend)
        if capture.isOpened() and capture.read()[0]:
            return capture
        capture.release()
    raise CameraUnavailableError(_troubleshooting_message(address))


def create_capture(address: CameraAddress, backend: int) -> cv2.VideoCapture:
    if isinstance(address, str):
        # Timeout só para URL: sem ele uma URL errada trava o programa; o Media
        # Foundation recusa esse parâmetro e deixaria de abrir a webcam.
        return cv2.VideoCapture(address, backend, [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, OPEN_TIMEOUT_MS])
    return cv2.VideoCapture(address, backend)


def candidate_backends(address: CameraAddress) -> List[int]:
    if isinstance(address, str):
        return [cv2.CAP_FFMPEG, cv2.CAP_ANY]
    if sys.platform.startswith("win"):
        return [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
    return [cv2.CAP_ANY]


def parse_camera_address(text: str) -> CameraAddress:
    text = text.strip()
    return int(text) if text.isdigit() else text


def _troubleshooting_message(address: CameraAddress) -> str:
    if isinstance(address, str):
        return (
            f"Não chegou imagem pela URL '{address}'.\n"
            "  - O PC e o celular estão na mesma rede Wi-Fi?\n"
            "  - Abra essa URL no navegador: se não aparecer vídeo, o problema é rede/app, não o programa.\n"
            "  - Feche o cliente DroidCam do PC: o app do celular aceita só uma conexão por vez.\n"
            "  - Use o endereço mostrado no app, terminando em /video (ex.: http://192.168.0.10:4747/video)."
        )
    return (
        f"Não chegou imagem pela câmera de índice {address}.\n"
        "  - Rode diagnosticar_camera.bat para ver quais índices funcionam.\n"
        "  - O cliente DroidCam do PC precisa estar aberto e CONECTADO (com vídeo aparecendo nele).\n"
        "  - Feche outros programas que usam câmera (Teams, navegador, OBS...)."
    )
