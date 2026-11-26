"""Procura câmeras que entregam imagem: python -m calibracao_branco.diagnostico [URL]"""

import sys

import cv2

from .camera import candidate_backends, create_capture, parse_camera_address

MAXIMUM_INDEX_TO_TRY = 5
BACKEND_NAMES = {cv2.CAP_DSHOW: "DirectShow", cv2.CAP_MSMF: "MediaFoundation",
                 cv2.CAP_FFMPEG: "FFmpeg", cv2.CAP_ANY: "automatico"}


def describe_address(address) -> str:
    results = [_try_backend(address, backend) for backend in candidate_backends(address)]
    return f"  {str(address):<40} " + " | ".join(results)


def _try_backend(address, backend: int) -> str:
    capture = create_capture(address, backend)
    try:
        if not capture.isOpened():
            return f"{BACKEND_NAMES[backend]}: nao abre"
        frame_was_read, frame = capture.read()
        if not frame_was_read:
            return f"{BACKEND_NAMES[backend]}: abre, SEM imagem"
        height, width = frame.shape[:2]
        return f"{BACKEND_NAMES[backend]}: OK {width}x{height}"
    finally:
        capture.release()


def main(arguments) -> None:
    addresses = [parse_camera_address(text) for text in arguments] or list(range(MAXIMUM_INDEX_TO_TRY + 1))
    print(f"OpenCV {cv2.__version__}. Testando cameras (pode demorar alguns segundos)...\n")
    for address in addresses:
        print(describe_address(address))
    print("\nUse no calibrar.bat um indice/URL que mostre 'OK'.")


if __name__ == "__main__":
    main(sys.argv[1:])
