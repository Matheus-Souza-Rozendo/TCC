import argparse
import sys
from pathlib import Path
from typing import List

from . import preview
from .camera import FrameSource, OpenCvCameraAdapter, parse_camera_address
from .calibrator import WhiteBalanceCalibrator
from .errors import CalibrationError
from .gain_file import CalibrationResult, GainFileWriter
from .gain_strategies import GainStrategyFactory
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
    region = _choose_region(camera, options.regiao)
    calibrator = WhiteBalanceCalibrator(
        WhiteReferenceSampler(camera, SamplingSettings(frames_to_average=options.quadros)),
        GainStrategyFactory.create(options.estrategia),
    )
    print(f"Medindo o gabarito na região {region.to_text()} ({options.quadros} quadros)...")
    result = calibrator.calibrate(region)
    GainFileWriter().write(result, Path(options.saida))
    _print_summary(result, options.saida)
    if not options.sem_conferencia:
        preview.show_corrected_comparison(camera, result.gains)


def _choose_region(camera: FrameSource, region_text: str) -> RegionOfInterest:
    if region_text:
        return RegionOfInterest.from_text(region_text)
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
    parser.add_argument("--sem-conferencia", action="store_true",
                        help="Não abre a janela de comparação original x corrigido no final.")
    return parser


def _positive_integer(text: str) -> int:
    value = int(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("precisa ser maior que zero")
    return value
