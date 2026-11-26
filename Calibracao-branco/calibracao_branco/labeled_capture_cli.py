"""Captura do dataset próprio com rótulos: python -m calibracao_branco.labeled_capture_cli --help

Fluxo por tomate:
1. No terminal: defeitos, maturação e diâmetro do paquímetro (os dois últimos opcionais).
2. Na janela da câmera: ESPAÇO tira uma foto (gire o tomate entre as fotos),
   ENTER passa para o próximo tomate, ESC encerra a sessão.
"""

import argparse
import sys
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional, TypeVar

from .camera import FrameSource, OpenCvCameraAdapter, average_frames, parse_camera_address
from .errors import CalibrationError
from .gain_file import GainFileReader
from .labeled_capture import (DEFECT_CODES, MATURITY_CODES, LabeledPhotoStore, TomatoLabels, parse_defects,
                              parse_maturity, parse_optional_diameter)
from .preview import DEFAULT_DISPLAY_WIDTH, KEY_ESCAPE, KEYS_CONFIRM, CalibrationPreview
from .region import RegionOfInterest
from .scale_overlay import draw_region

KEY_SPACE = 32
FRAMES_PER_PHOTO = 3
END_SESSION_WORD = "sair"
ParsedValue = TypeVar("ParsedValue")


class CaptureOutcome(Enum):
    NEXT_TOMATO = "proximo"
    END_SESSION = "encerrar"


def main(arguments: List[str] = None) -> int:
    options = _build_parser().parse_args(arguments)
    try:
        _run_session(options)
    except (CalibrationError, ValueError) as error:
        print(f"ERRO: {error}", file=sys.stderr)
        return 1
    return 0


def _run_session(options: argparse.Namespace) -> None:
    gain_file = Path(options.gain)
    region = GainFileReader().read_region(gain_file)
    camera_address = options.camera or GainFileReader().read_camera_address(gain_file)
    store = LabeledPhotoStore(Path(options.pasta))
    with OpenCvCameraAdapter(parse_camera_address(camera_address)) as camera:
        session = TomatoPhotoSession(camera, store, region, CalibrationPreview(options.largura_janela))
        while True:
            labels = _ask_labels(store.next_tomato_id())
            if labels is None or session.capture_photos(labels) is CaptureOutcome.END_SESSION:
                break
    print(f"\nSessao encerrada: {session.photos_taken} foto(s) nova(s) em {Path(options.pasta).resolve()}")


def _ask_labels(tomato_id: int) -> Optional[TomatoLabels]:
    """Pergunta os rótulos no terminal. Devolve None se o operador digitar 'sair'."""
    print(f"\n===== Tomate {tomato_id} =====")
    defect_help = ", ".join(f"{code}={name}" for code, name in DEFECT_CODES.items())
    defects_text = input(f"Defeitos ({defect_help}; varias letras juntas, ex.: rp; ENTER = sadio; "
                         f"'{END_SESSION_WORD}' = encerrar): ")
    if defects_text.strip().lower() == END_SESSION_WORD:
        return None
    defects = _parse_until_valid(defects_text, parse_defects, "Defeitos: ")
    maturity_help = ", ".join(f"{code}={name}" for code, name in MATURITY_CODES.items())
    maturity = _parse_until_valid(input(f"Maturacao ({maturity_help}; ENTER = nao informar): "),
                                  parse_maturity, "Maturacao: ")
    diameter = _parse_until_valid(input("Diametro no paquimetro em mm (ENTER = nao informar): "),
                                  parse_optional_diameter, "Diametro: ")
    labels = TomatoLabels(tomato_id, defects, maturity, diameter)
    print(f"-> {labels.describe()}")
    print("Na janela: ESPACO = foto (gire o tomate entre as fotos) | ENTER = proximo tomate | ESC = encerrar")
    return labels


def _parse_until_valid(text: str, parser: Callable[[str], ParsedValue], retry_prompt: str) -> ParsedValue:
    while True:
        try:
            return parser(text)
        except ValueError as error:
            print(f"  {error}")
            text = input(retry_prompt)


class TomatoPhotoSession:
    """Janela da câmera com a região de interesse; tira as fotos de um tomate por vez."""

    def __init__(self, camera: FrameSource, store: LabeledPhotoStore, region: RegionOfInterest,
                 preview: CalibrationPreview):
        self._camera = camera
        self._store = store
        self._region = region
        self._preview = preview
        self.photos_taken = 0

    def capture_photos(self, labels: TomatoLabels) -> CaptureOutcome:
        photos_of_tomato = 0
        try:
            while True:
                caption = (f"Tomate {labels.tomato_id}: {photos_of_tomato} foto(s) | ESPACO = foto | "
                           f"ENTER = proximo | ESC = encerrar")
                key = self._preview.show_and_read_key(draw_region(self._camera.read_frame(), self._region), caption)
                if key == KEY_SPACE:
                    self._save_photo(labels)
                    photos_of_tomato += 1
                elif key in KEYS_CONFIRM:
                    return CaptureOutcome.NEXT_TOMATO
                elif key == KEY_ESCAPE:
                    return CaptureOutcome.END_SESSION
        finally:
            # Fecha a janela antes de voltar ao terminal: parada, ela ficaria "Não respondendo".
            self._preview.close_windows()

    def _save_photo(self, labels: TomatoLabels) -> None:
        # A foto é a imagem limpa da câmera (média de quadros); a região amarela é só da tela.
        saved = self._store.save(average_frames(self._camera, FRAMES_PER_PHOTO), labels)
        self.photos_taken += 1
        print(f"  foto salva: {saved.name}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m calibracao_branco.labeled_capture_cli",
                                     description="Captura fotos de tomates com rotulos de defeito, maturacao e diametro.")
    parser.add_argument("--gain", default="bancada.gain", help="De onde vem a regiao de interesse e a camera.")
    parser.add_argument("--camera", default="", help="Indice ou URL. Sem ela, usa a camera gravada no .gain.")
    parser.add_argument("--pasta", default="../Dataset-proprio", help="Pasta do dataset proprio (fotos/ e rotulos.csv).")
    parser.add_argument("--largura-janela", type=int, default=DEFAULT_DISPLAY_WIDTH, help="Largura da janela na tela.")
    return parser


if __name__ == "__main__":
    sys.exit(main())
