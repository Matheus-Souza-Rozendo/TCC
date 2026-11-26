import math
import unittest
from typing import List

import cv2
import numpy as np

from calibracao_branco.errors import NoObjectFoundError, ObjectTouchesRegionBorderError
from calibracao_branco.measurement_overlay import MeasuredObject, MeasurementOverlay
from calibracao_branco.object_measurement import CircularObjectMeasurer
from calibracao_branco.pixel_scale import CellScale, GridSize, PixelScaleMap, RegionGrid
from calibracao_branco.region import RegionOfInterest
from calibracao_branco.segmentation import DarkBackgroundSegmenter

FRAME_SHAPE = (300, 400, 3)
REGION = RegionOfInterest(20, 20, 360, 260)
BACKGROUND = (20, 20, 20)
COIN_COLOR = (190, 200, 210)
RADIUS_PX = 40


def black_background_with_coins(centers: List[tuple]) -> np.ndarray:
    rng = np.random.default_rng(0)
    frame = np.clip(np.full(FRAME_SHAPE, BACKGROUND, np.float64) + rng.normal(0, 3, FRAME_SHAPE), 0, 255)
    frame = frame.astype(np.uint8)
    for center in centers:
        # Borda nítida (sem antisserrilhado): assim o tamanho real é exatamente true_coin_area_px().
        cv2.circle(frame, center, RADIUS_PX, COIN_COLOR, -1)
    return frame


def true_coin_area_px() -> int:
    mask = np.zeros(FRAME_SHAPE[:2], np.uint8)
    cv2.circle(mask, (150, 150), RADIUS_PX, 255, -1)
    return int(np.count_nonzero(mask))


def scale_map_with(mm_per_pixel_by_column: List[float]) -> PixelScaleMap:
    """Grade de N colunas x 1 linha, cada coluna com a sua escala."""
    grid = RegionGrid(REGION, GridSize(columns=len(mm_per_pixel_by_column), rows=1))
    return PixelScaleMap(grid, [CellScale(cell, scale, 10, 0.0, 0.0)
                                for cell, scale in zip(grid.cells(), mm_per_pixel_by_column)])


def measure(frame: np.ndarray, scale_map: PixelScaleMap):
    measurer = CircularObjectMeasurer(scale_map)
    return [measurer.measure(segment) for segment in DarkBackgroundSegmenter().segment(frame, REGION)]


class SegmentationTests(unittest.TestCase):
    def test_finds_every_coin(self):
        frame = black_background_with_coins([(100, 100), (290, 200)])
        self.assertEqual(len(DarkBackgroundSegmenter().segment(frame, REGION)), 2)

    def test_dark_reflection_inside_coin_is_filled(self):
        frame = black_background_with_coins([(150, 150)])
        cv2.circle(frame, (150, 150), 15, BACKGROUND, -1)
        segment = DarkBackgroundSegmenter().segment(frame, REGION)[0]
        self.assertAlmostEqual(segment.area_px(), true_coin_area_px(), delta=0.01 * true_coin_area_px())

    def test_only_background_is_rejected(self):
        with self.assertRaises(NoObjectFoundError):
            DarkBackgroundSegmenter().segment(black_background_with_coins([]), REGION)

    def test_coin_cut_by_region_border_is_rejected(self):
        with self.assertRaises(ObjectTouchesRegionBorderError):
            DarkBackgroundSegmenter().segment(black_background_with_coins([(40, 150)]), REGION)


class MeasurementTests(unittest.TestCase):
    def test_uniform_scale_gives_same_size_with_and_without_correction(self):
        measurement = measure(black_background_with_coins([(150, 150)]), scale_map_with([0.5, 0.5]))[0]
        true_diameter_px = math.sqrt(4 * true_coin_area_px() / math.pi)
        self.assertAlmostEqual(measurement.diameter_px, true_diameter_px, delta=0.3)
        self.assertAlmostEqual(measurement.diameter_mm_region_corrected, true_diameter_px * 0.5, delta=0.15)
        self.assertAlmostEqual(measurement.diameter_mm_single_scale, measurement.diameter_mm_region_corrected, places=6)

    def test_coin_over_cell_border_uses_each_cell_scale(self):
        left_scale, right_scale = 0.5, 0.6
        border_x = REGION.x + REGION.width // 2
        measurement = measure(black_background_with_coins([(border_x, 150)]),
                              scale_map_with([left_scale, right_scale]))[0]
        half_area = measurement.area_px / 2
        expected_area_mm2 = half_area * left_scale ** 2 + half_area * right_scale ** 2
        self.assertAlmostEqual(measurement.diameter_mm_region_corrected,
                               math.sqrt(4 * expected_area_mm2 / math.pi), delta=0.2)
        self.assertEqual([share.cell_label for share in measurement.cell_shares], ["0_0", "0_1"])
        self.assertAlmostEqual(measurement.cell_shares[0].fraction, 0.5, delta=0.03)

    def test_coin_inside_one_cell_uses_only_that_cell(self):
        measurement = measure(black_background_with_coins([(100, 150)]), scale_map_with([0.5, 0.6]))[0]
        self.assertEqual([share.cell_label for share in measurement.cell_shares], ["0_0"])
        self.assertAlmostEqual(measurement.diameter_mm_region_corrected, measurement.diameter_px * 0.5, places=6)

    def test_coin_is_recognized_as_circular(self):
        measurement = measure(black_background_with_coins([(150, 150)]), scale_map_with([0.5]))[0]
        self.assertTrue(measurement.looks_circular())


class OverlayTests(unittest.TestCase):
    def test_reference_diameter_shows_error(self):
        frame = black_background_with_coins([(150, 150)])
        scale_map = scale_map_with([0.5])
        segment = DarkBackgroundSegmenter().segment(frame, REGION)[0]
        measured = MeasuredObject(segment, CircularObjectMeasurer(scale_map).measure(segment))
        overlay = MeasurementOverlay(scale_map, reference_diameter_mm=40.0)
        self.assertTrue(any(line.startswith("real 40.00 mm | erro") for line in overlay.describe(1, measured.measurement)))
        self.assertEqual(overlay.draw(frame, [measured]).shape, frame.shape)


if __name__ == "__main__":
    unittest.main()
