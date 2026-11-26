"""Teste de medição de objeto circular: python -m calibracao_branco.measurement_cli --help"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import numpy as np

from .camera import OpenCvCameraAdapter, average_frames, parse_camera_address
from .errors import CalibrationError
from .gain_file import GainFileReader, apply_gains
from .image_files import load_image, save_image
from .measurement_overlay import MeasuredObject, MeasurementOverlay
from .object_measurement import CircularObjectMeasurer
from .pixel_scale import PixelScaleMap
from .preview import DEFAULT_DISPLAY_WIDTH, CalibrationPreview
from .scale_file import ScaleSectionReader
from .scale_overlay import RegionOverlayFrameSourceDecorator
from .segmentation import DarkBackgroundSegmenter

FRAMES_TO_AVERAGE = 5


def main(arguments: List[str] = None) -> int:
    options = _build_parser().parse_args(arguments)
    try:
        _run_measurement(options)
    except (CalibrationError, ValueError) as error:
        print(f"ERRO: {error}", file=sys.stderr)
        return 1
    return 0


def _run_measurement(options: argparse.Namespace) -> None:
    gain_file = Path(options.gain)
    gains = GainFileReader().read_gains(gain_file)
    scale_map = ScaleSectionReader().read(gain_file)
    preview = CalibrationPreview(options.largura_janela)
    output_base = Path(options.pasta_saida) / f"medicao_{datetime.now():%Y%m%d_%H%M%S}"

    frame = _acquire_frame(options, scale_map, preview)
    if not options.imagem:
        save_image(frame, output_base.with_name(output_base.name + "_original.png"))

    balanced = apply_gains(frame, gains)
    measurer = CircularObjectMeasurer(scale_map)
    measured_objects = [MeasuredObject(segment, measurer.measure(segment))
                        for segment in DarkBackgroundSegmenter().segment(balanced, scale_map.grid.region)]

    overlay = MeasurementOverlay(scale_map, options.diametro_real_mm)
    result_image = overlay.draw(balanced, measured_objects)
    save_image(result_image, output_base.with_suffix(".png"))
    _print_summary(overlay, measured_objects, output_base)
    if not options.sem_conferencia:
        preview.show_until_key(result_image, "Resultado da medicao")


def _acquire_frame(options: argparse.Namespace, scale_map: PixelScaleMap, preview: CalibrationPreview) -> np.ndarray:
    if options.imagem:
        return load_image(Path(options.imagem))
    camera_address = options.camera or GainFileReader().read_camera_address(Path(options.gain))
    with OpenCvCameraAdapter(parse_camera_address(camera_address)) as camera:
        preview.wait_for_operator_ready(RegionOverlayFrameSourceDecorator(camera, scale_map.grid.region),
                                        "Coloque o objeto dentro da area amarela.")
        return average_frames(camera, FRAMES_TO_AVERAGE)


def _print_summary(overlay: MeasurementOverlay, measured_objects: List[MeasuredObject], output_base: Path) -> None:
    print(f"{len(measured_objects)} objeto(s) encontrado(s).")
    for number, measured in enumerate(measured_objects, start=1):
        for line in overlay.describe(number, measured.measurement):
            print(f"  {line}")
    print(f"Imagem com o resultado salva em: {output_base.with_suffix('.png').resolve()}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m calibracao_branco.measurement_cli",
        description="Segmenta objetos claros sobre o fundo preto e mede o diâmetro com e sem a correção por região.",
    )
    parser.add_argument("--gain", default="bancada.gain", help="Arquivo .gain com o branco e a escala calibrados.")
    parser.add_argument("--camera", default="", help="Índice ou URL. Sem ela, usa a câmera gravada no .gain.")
    parser.add_argument("--imagem", default="", help="Mede uma imagem salva em vez de capturar pela câmera.")
    parser.add_argument("--diametro-real-mm", type=_optional_positive_number, default=None,
                        help="Diâmetro real do objeto (ex.: moeda de R$ 1 = 27). Mostra o erro da medição.")
    parser.add_argument("--pasta-saida", default="medicoes", help="Pasta das imagens de resultado.")
    parser.add_argument("--largura-janela", type=int, default=DEFAULT_DISPLAY_WIDTH, help="Largura das janelas na tela.")
    parser.add_argument("--sem-conferencia", action="store_true", help="Não abre a janela com o resultado.")
    return parser


def _optional_positive_number(text: str) -> Optional[float]:
    if not text.strip():
        return None
    value = float(text.replace(",", "."))
    if value <= 0:
        raise argparse.ArgumentTypeError("precisa ser maior que zero")
    return value


if __name__ == "__main__":
    sys.exit(main())
