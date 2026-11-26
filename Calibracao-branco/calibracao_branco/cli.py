import argparse
import sys
from pathlib import Path
from typing import List

import numpy as np

from .camera import FrameSource, OpenCvCameraAdapter, parse_camera_address
from .calibrator import WhiteBalanceCalibrator
from .comparison import build_comparison, save_image
from .errors import CalibrationError
from .gain_file import CalibrationResult, GainFileWriter
from .gain_strategies import GainStrategyFactory
from .preview import DEFAULT_DISPLAY_WIDTH, CalibrationPreview
from .region import RegionOfInterest
from .sampling import SamplingSettings, WhiteReferenceSampler


def main(arguments: List[str] = None) -> int:
    options = _build_parser().parse_args(arguments)
    try:
        with OpenCvCameraAdapter(parse_camera_address(options.camera)) as camera:
            _run_calibration(camera, options)
    except CalibrationError as error:
        print(f"ERRO: {error}", file=sys.stderr)
        return 1
    return 0


def _run_calibration(camera: FrameSource, options: argparse.Namespace) -> None:
    preview = CalibrationPreview(options.largura_janela)
    region = RegionOfInterest.from_text(options.regiao) if options.regiao else _select_region_on_screen(preview, camera)
    calibrator = WhiteBalanceCalibrator(
        WhiteReferenceSampler(camera, SamplingSettings(frames_to_average=options.quadros)),
        GainStrategyFactory.create(options.estrategia),
    )
    print(f"Medindo o gabarito na região {region.to_text()} ({options.quadros} quadros)...")
    result = calibrator.calibrate(region)
    GainFileWriter().write(result, Path(options.saida))
    _print_summary(result, options.saida)
    if options.foto_comparacao:
        _save_comparison_photo(build_comparison(camera.read_frame(), result.gains), Path(options.foto_comparacao))
    if not options.sem_conferencia:
        preview.show_corrected_comparison(camera, result.gains)


def _save_comparison_photo(comparison: np.ndarray, destination: Path) -> None:
    save_image(comparison, destination)
    print(f"Foto antes x depois salva em: {destination.resolve()}")


def _select_region_on_screen(preview: CalibrationPreview, camera: FrameSource) -> RegionOfInterest:
    frame = preview.wait_for_operator_ready(camera)
    return preview.select_region(frame)


def _print_summary(result: CalibrationResult, destination: str) -> None:
    means, gains = result.sample.channel_means, result.gains
    print(f"Média do branco  R={means.red:7.2f}  G={means.green:7.2f}  B={means.blue:7.2f}")
    print(f"Ganho            R={gains.red:7.4f}  G={gains.green:7.4f}  B={gains.blue:7.4f}")
    for warning in result.sample.warnings:
        print(f"AVISO: {warning}")
    print(f"Arquivo salvo em: {Path(destination).resolve()}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m calibracao_branco",
        description="Mede um gabarito branco pela câmera e gera um arquivo .gain com o ganho de cada canal.",
    )
    parser.add_argument("--camera", default="0",
                        help="Índice da webcam (DroidCam costuma ser 0, 1 ou 2) ou URL, ex.: http://192.168.0.10:4747/video")
    parser.add_argument("--saida", default="calibracao.gain", help="Caminho do arquivo .gain gerado.")
    parser.add_argument("--estrategia", default="referencia_verde", choices=GainStrategyFactory.available_names(),
                        help="referencia_verde: só corrige a cor. nivel_alvo: leva o branco a 230 (cor + brilho).")
    parser.add_argument("--regiao", default="",
                        help="Região fixa do gabarito 'x,y,largura,altura'. Sem ela, você seleciona com o mouse.")
    parser.add_argument("--quadros", type=_positive_integer, default=30, help="Quadros usados na média.")
    parser.add_argument("--largura-janela", type=_positive_integer, default=DEFAULT_DISPLAY_WIDTH,
                        help="Largura em pixels das janelas na tela (a altura segue a proporção). Não afeta a medição.")
    parser.add_argument("--foto-comparacao", default="",
                        help="Salva uma foto antes x depois (resolução original) neste caminho .png ou .jpg.")
    parser.add_argument("--sem-conferencia", action="store_true",
                        help="Não abre a janela de comparação original x corrigido no final.")
    return parser


def _positive_integer(text: str) -> int:
    value = int(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("precisa ser maior que zero")
    return value
