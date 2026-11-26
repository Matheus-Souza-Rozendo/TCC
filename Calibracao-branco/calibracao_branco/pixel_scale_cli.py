"""Calibração pixel -> mm por região: python -m calibracao_branco.pixel_scale_cli --help"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from .camera import FrameSource, OpenCvCameraAdapter, average_frames, parse_camera_address
from .chessboard import ChessboardDetector
from .errors import CalibrationError
from .gain_file import GainFileReader
from .image_files import save_image
from .pixel_scale import GridSize, PixelScaleCalibrator, RegionGrid
from .preview import DEFAULT_DISPLAY_WIDTH, CalibrationPreview
from .scale_file import ScaleCalibrationResult, ScaleSectionWriter, tolerance_warnings
from .scale_overlay import RegionOverlayFrameSourceDecorator, draw_scale_map

FRAMES_TO_AVERAGE = 10


def main(arguments: List[str] = None) -> int:
    options = _build_parser().parse_args(arguments)
    try:
        with OpenCvCameraAdapter(parse_camera_address(_camera_address(options))) as camera:
            _run_scale_calibration(camera, options)
    except (CalibrationError, ValueError) as error:
        print(f"ERRO: {error}", file=sys.stderr)
        return 1
    return 0


def _camera_address(options: argparse.Namespace) -> str:
    """Sem --camera, usa a mesma câmera da calibração de branco, gravada no .gain."""
    return options.camera or GainFileReader().read_camera_address(Path(options.gain))


def _run_scale_calibration(camera: FrameSource, options: argparse.Namespace) -> None:
    gain_file = Path(options.gain)
    region = GainFileReader().read_region(gain_file)
    grid = RegionGrid(region, GridSize.from_text(options.grade))
    print(f"Região de interesse (do {gain_file.name}): {region.to_text()} | grade {grid.size.to_text()}")

    preview = CalibrationPreview(options.largura_janela)
    preview.wait_for_operator_ready(RegionOverlayFrameSourceDecorator(camera, region),
                                    "Cubra a area amarela com o tabuleiro.")
    print(f"Detectando o tabuleiro (média de {FRAMES_TO_AVERAGE} quadros)...")
    frame = average_frames(camera, FRAMES_TO_AVERAGE)
    detection = ChessboardDetector().detect(frame)
    print(f"Tabuleiro encontrado: {detection.size_text()} cantos internos visíveis.")
    scale_map = PixelScaleCalibrator(options.quadrado_mm, grid).calibrate(detection.corners)

    result = ScaleCalibrationResult(scale_map, detection, options.quadrado_mm, datetime.now())
    ScaleSectionWriter().write(result, gain_file)
    _print_summary(result, gain_file)
    _present_detection(draw_scale_map(frame, detection, scale_map), options, preview)


def _present_detection(detection_image, options: argparse.Namespace, preview: CalibrationPreview) -> None:
    if options.foto_deteccao:
        save_image(detection_image, Path(options.foto_deteccao))
        print(f"Foto da detecção salva em: {Path(options.foto_deteccao).resolve()}")
    if not options.sem_conferencia:
        preview.show_until_key(detection_image, "Verde = erro dentro de 0,5 mm | Vermelho = fora")


def _print_summary(result: ScaleCalibrationResult, destination: Path) -> None:
    scale_map = result.scale_map
    print(f"mm/pixel médio: {scale_map.mean_mm_per_pixel():.5f}   erro máximo: {scale_map.max_error_mm():.3f} mm")
    for cell_scale in scale_map.cell_scales:
        print(f"  célula {cell_scale.cell.label()}: {cell_scale.mm_per_pixel:.5f} mm/px  "
              f"erro máx {cell_scale.max_error_mm:.3f} mm  ({cell_scale.segment_count} trechos)")
    for warning in tolerance_warnings(scale_map):
        print(f"AVISO: {warning}")
    print(f"Escala gravada no arquivo: {destination.resolve()}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m calibracao_branco.pixel_scale_cli",
        description="Mede um tabuleiro de xadrez na região do .gain e grava nele a escala mm/pixel por região.",
    )
    parser.add_argument("--gain", default="bancada.gain",
                        help="Arquivo .gain: a região de interesse vem dele e a escala é gravada nele.")
    parser.add_argument("--camera", default="",
                        help="Índice da webcam ou URL. Sem ela, usa a câmera gravada no .gain pelo calibrar.bat.")
    parser.add_argument("--quadrado-mm", type=_positive_number, required=True,
                        help="Lado de um quadrado em mm, MEDIDO COM RÉGUA no papel impresso.")
    parser.add_argument("--grade", default="3x3", help="Em quantas células dividir a região (colunas x linhas).")
    parser.add_argument("--foto-deteccao", default="", help="Salva a imagem com cantos e células neste .png/.jpg.")
    parser.add_argument("--largura-janela", type=int, default=DEFAULT_DISPLAY_WIDTH, help="Largura das janelas na tela.")
    parser.add_argument("--sem-conferencia", action="store_true", help="Não abre a janela de conferência no final.")
    return parser


def _positive_number(text: str) -> float:
    value = float(text.replace(",", "."))
    if value <= 0:
        raise argparse.ArgumentTypeError("precisa ser maior que zero")
    return value


if __name__ == "__main__":
    sys.exit(main())
