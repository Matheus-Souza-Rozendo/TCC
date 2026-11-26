import sys
from typing import Protocol, Union

import cv2
import numpy as np

from .errors import CameraUnavailableError

CameraAddress = Union[int, str]


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
        self._capture = self._open_capture(address)

    def read_frame(self) -> np.ndarray:
        frame_was_read, frame = self._capture.read()
        if not frame_was_read:
            raise CameraUnavailableError(f"Não foi possível ler um quadro da câmera '{self._address}'.")
        return frame

    def close(self) -> None:
        self._capture.release()

    def __enter__(self) -> "OpenCvCameraAdapter":
        return self

    def __exit__(self, *exception_info) -> None:
        self.close()

    @staticmethod
    def _open_capture(address: CameraAddress) -> cv2.VideoCapture:
        capture = cv2.VideoCapture(address, _preferred_backend(address))
        if not capture.isOpened():
            raise CameraUnavailableError(
                f"Câmera '{address}' não abriu. Confira se o DroidCam está conectado "
                "e se o índice/URL está correto (teste outros índices: 0, 1, 2...)."
            )
        return capture


def parse_camera_address(text: str) -> CameraAddress:
    return int(text) if text.isdigit() else text


def _preferred_backend(address: CameraAddress) -> int:
    # No Windows a webcam virtual do DroidCam abre de forma mais estável via DirectShow.
    if isinstance(address, int) and sys.platform.startswith("win"):
        return cv2.CAP_DSHOW
    return cv2.CAP_ANY
