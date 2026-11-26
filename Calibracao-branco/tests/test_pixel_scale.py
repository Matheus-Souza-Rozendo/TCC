import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import numpy as np

from calibracao_branco.calibration_sections import read_sections
from calibracao_branco.channels import ChannelValues
from calibracao_branco.chessboard import ChessboardDetector
from calibracao_branco.errors import (CalibrationFileFormatError, ChessboardNotFoundError,
                                      IncompleteRegionCoverageError)
from calibracao_branco.gain_file import CalibrationResult, GainFileReader, GainFileWriter
from calibracao_branco.pixel_scale import GridSize, PixelScaleCalibrator, RegionGrid
from calibracao_branco.region import RegionOfInterest
from calibracao_branco.sampling import WhiteReferenceSample
from calibracao_branco.scale_file import ScaleCalibrationResult, ScaleSectionReader, ScaleSectionWriter

SQUARE_PX = 40
MARGIN_PX = 60
SQUARE_MM = 20.0
INNER_COLUMNS, INNER_ROWS = 9, 6
REGION_INSIDE_BOARD = RegionOfInterest(90, 90, 340, 260)
FIXED_TIME = datetime(2026, 1, 1, 12, 0, 0)


def draw_chessboard() -> np.ndarray:
    """Tabuleiro de 10 x 7 quadrados (9 x 6 cantos internos), cada quadrado com SQUARE_PX."""
    columns, rows = INNER_COLUMNS + 1, INNER_ROWS + 1
    image = np.full((rows * SQUARE_PX + 2 * MARGIN_PX, columns * SQUARE_PX + 2 * MARGIN_PX, 3), 255, np.uint8)
    for row in range(rows):
        for column in range(columns):
            if (row + column) % 2 == 0:
                top, left = MARGIN_PX + row * SQUARE_PX, MARGIN_PX + column * SQUARE_PX
                image[top:top + SQUARE_PX, left:left + SQUARE_PX] = 0
    return image


def calibrate(region: RegionOfInterest, grid_text: str = "2x2"):
    corners = ChessboardDetector().detect(draw_chessboard()).corners
    return PixelScaleCalibrator(SQUARE_MM, RegionGrid(region, GridSize.from_text(grid_text))).calibrate(corners)


def scale_result(region: RegionOfInterest) -> ScaleCalibrationResult:
    detection = ChessboardDetector().detect(draw_chessboard())
    return ScaleCalibrationResult(calibrate(region), detection, SQUARE_MM, FIXED_TIME)


def white_balance_result(region: RegionOfInterest) -> CalibrationResult:
    sample = WhiteReferenceSample(ChannelValues(200, 200, 200), ChannelValues(0.01, 0.01, 0.01), 30)
    return CalibrationResult(ChannelValues(1, 1, 1), sample, region, "referencia_verde", FIXED_TIME, "1")


class ChessboardDetectionTests(unittest.TestCase):
    def test_finds_corner_count_without_being_told(self):
        detection = ChessboardDetector().detect(draw_chessboard())
        self.assertEqual((detection.columns, detection.rows), (INNER_COLUMNS, INNER_ROWS))

    def test_board_cut_by_image_border_is_still_detected(self):
        cut_board = np.ascontiguousarray(draw_chessboard()[110:, 130:])
        detection = ChessboardDetector().detect(cut_board)
        self.assertLess(detection.columns * detection.rows, INNER_COLUMNS * INNER_ROWS)
        neighbor_distance = np.linalg.norm(detection.corners[0, 1] - detection.corners[0, 0])
        self.assertAlmostEqual(neighbor_distance, SQUARE_PX, delta=0.5)

    def test_image_without_board_is_rejected(self):
        with self.assertRaises(ChessboardNotFoundError):
            ChessboardDetector().detect(np.full((300, 300, 3), 255, np.uint8))


class PixelScaleTests(unittest.TestCase):
    def test_every_cell_gets_known_scale(self):
        scale_map = calibrate(REGION_INSIDE_BOARD)
        for cell_scale in scale_map.cell_scales:
            self.assertAlmostEqual(cell_scale.mm_per_pixel, SQUARE_MM / SQUARE_PX, places=2)
            self.assertLess(cell_scale.max_error_mm, 0.5)

    def test_grid_cells_cover_region_without_gaps(self):
        cells = RegionGrid(RegionOfInterest(10, 10, 101, 50), GridSize(columns=3, rows=2)).cells()
        self.assertEqual(sum(cell.region.width * cell.region.height for cell in cells), 101 * 50)

    def test_region_larger_than_board_is_rejected(self):
        with self.assertRaises(IncompleteRegionCoverageError):
            calibrate(RegionOfInterest(0, 0, 520, 400), "4x4")

    def test_point_outside_calibrated_region_is_rejected(self):
        with self.assertRaises(ValueError):
            calibrate(REGION_INSIDE_BOARD).mm_per_pixel_at(5, 5)


class GainFileSectionsTests(unittest.TestCase):
    def setUp(self):
        self._folder = tempfile.TemporaryDirectory()
        self.gain_file = Path(self._folder.name) / "bancada.gain"
        GainFileWriter().write(white_balance_result(REGION_INSIDE_BOARD), self.gain_file)
        ScaleSectionWriter().write(scale_result(REGION_INSIDE_BOARD), self.gain_file)

    def tearDown(self):
        self._folder.cleanup()

    def test_scale_is_read_back_from_gain_file(self):
        scale_map = ScaleSectionReader().read(self.gain_file)
        self.assertAlmostEqual(scale_map.mm_per_pixel_at(150, 150), SQUARE_MM / SQUARE_PX, places=2)

    def test_scale_does_not_break_gain_reading(self):
        self.assertEqual(GainFileReader().read_region(self.gain_file), REGION_INSIDE_BOARD)
        self.assertAlmostEqual(GainFileReader().read_gains(self.gain_file).red, 1.0)

    def test_new_white_balance_in_same_region_keeps_scale(self):
        GainFileWriter().write(white_balance_result(REGION_INSIDE_BOARD), self.gain_file)
        self.assertTrue(read_sections(self.gain_file).scale_lines)

    def test_new_white_balance_in_other_region_discards_old_scale(self):
        GainFileWriter().write(white_balance_result(RegionOfInterest(0, 0, 50, 50)), self.gain_file)
        self.assertFalse(read_sections(self.gain_file).scale_lines)

    def test_scale_requires_white_balance_first(self):
        empty_gain_file = Path(self._folder.name) / "vazio.gain"
        with self.assertRaises(CalibrationFileFormatError):
            ScaleSectionWriter().write(scale_result(REGION_INSIDE_BOARD), empty_gain_file)

    def test_camera_used_for_white_balance_is_reused(self):
        self.assertEqual(GainFileReader().read_camera_address(self.gain_file), "1")

    def test_old_gain_file_without_camera_uses_default(self):
        old_gain_file = Path(self._folder.name) / "antigo.gain"
        old_gain_file.write_text("regiao_gabarito=0,0,10,10", encoding="utf-8")
        self.assertEqual(GainFileReader().read_camera_address(old_gain_file), "0")


if __name__ == "__main__":
    unittest.main()
