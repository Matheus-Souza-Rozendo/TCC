import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import numpy as np

from calibracao_branco.calibrator import WhiteBalanceCalibrator
from calibracao_branco.channels import ChannelValues
from calibracao_branco.comparison import build_comparison, save_image
from calibracao_branco.errors import WhiteReferenceSaturatedError, WhiteReferenceTooDarkError
from calibracao_branco.gain_file import GainFileReader, GainFileWriter, apply_gains
from calibracao_branco.gain_strategies import GreenReferenceGainStrategy, TargetLevelGainStrategy
from calibracao_branco.region import RegionOfInterest
from calibracao_branco.sampling import SamplingSettings, WhiteReferenceSampler

FIXED_TIME = datetime(2026, 1, 1, 12, 0, 0)
WHOLE_FRAME = RegionOfInterest(0, 0, 40, 30)


class SolidColorFrameSource:
    """Câmera falsa que sempre entrega um quadro de cor única (em BGR)."""

    def __init__(self, bgr_color):
        self._frame = np.full((30, 40, 3), bgr_color, dtype=np.uint8)

    def read_frame(self) -> np.ndarray:
        return self._frame.copy()

    def close(self) -> None:
        pass


def calibrate_solid_color(bgr_color, strategy=None):
    sampler = WhiteReferenceSampler(SolidColorFrameSource(bgr_color), SamplingSettings(2, 3))
    calibrator = WhiteBalanceCalibrator(sampler, strategy or GreenReferenceGainStrategy(), lambda: FIXED_TIME)
    return calibrator.calibrate(WHOLE_FRAME)


class GainCalculationTests(unittest.TestCase):
    def test_green_reference_equalizes_bluish_white(self):
        result = calibrate_solid_color((200, 160, 120))
        self.assertAlmostEqual(result.gains.red, 160 / 120)
        self.assertAlmostEqual(result.gains.green, 1.0)
        self.assertAlmostEqual(result.gains.blue, 160 / 200)

    def test_target_level_brings_every_channel_to_target(self):
        result = calibrate_solid_color((200, 160, 100), TargetLevelGainStrategy(230))
        self.assertAlmostEqual(result.gains.blue * 200, 230)
        self.assertAlmostEqual(result.gains.red * 100, 230)

    def test_applying_gains_turns_reference_gray(self):
        result = calibrate_solid_color((200, 160, 120))
        corrected = apply_gains(np.full((2, 2, 3), (200, 160, 120), dtype=np.uint8), result.gains)
        self.assertTrue(np.all(np.abs(corrected.astype(int) - 160) <= 1))


class WhiteReferenceValidationTests(unittest.TestCase):
    def test_saturated_reference_is_rejected(self):
        with self.assertRaises(WhiteReferenceSaturatedError):
            calibrate_solid_color((255, 200, 200))

    def test_dark_reference_is_rejected(self):
        with self.assertRaises(WhiteReferenceTooDarkError):
            calibrate_solid_color((30, 120, 120))

    def test_region_outside_frame_is_rejected(self):
        with self.assertRaises(ValueError):
            RegionOfInterest(30, 20, 20, 20).crop(np.zeros((30, 40, 3), dtype=np.uint8))


class RegionScalingTests(unittest.TestCase):
    def test_region_selected_on_reduced_screen_maps_back_to_original(self):
        on_screen = RegionOfInterest(100, 50, 200, 150)
        self.assertEqual(on_screen.scaled(2.0), RegionOfInterest(200, 100, 400, 300))

    def test_scaled_region_stays_inside_original_frame(self):
        screen_scale = 960 / 1920
        whole_screen = RegionOfInterest(0, 0, 960, 540)
        original_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        cropped = whole_screen.scaled(1 / screen_scale).crop(original_frame)
        self.assertEqual(cropped.shape[:2], (1080, 1920))


class ComparisonPhotoTests(unittest.TestCase):
    def test_comparison_has_before_and_after_side_by_side(self):
        original = np.full((30, 40, 3), (200, 160, 120), dtype=np.uint8)
        comparison = build_comparison(original, ChannelValues(red=160 / 120, green=1.0, blue=0.8))
        self.assertEqual(comparison.shape, (30, 80, 3))
        self.assertTrue(np.all(np.abs(comparison[-1, -1].astype(int) - 160) <= 1))

    def test_photo_is_saved_even_with_accents_in_path(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "calibração" / "comparação.png"
            save_image(np.zeros((10, 20, 3), dtype=np.uint8), destination)
            self.assertGreater(destination.stat().st_size, 0)


class GainFileTests(unittest.TestCase):
    def test_written_gains_are_read_back(self):
        result = calibrate_solid_color((200, 160, 120))
        with tempfile.TemporaryDirectory() as folder:
            gain_path = Path(folder) / "bancada.gain"
            GainFileWriter().write(result, gain_path)
            loaded = GainFileReader().read_gains(gain_path)
        self.assertAlmostEqual(loaded.red, result.gains.red, places=5)
        self.assertAlmostEqual(loaded.blue, result.gains.blue, places=5)

    def test_channel_order_is_converted_from_bgr(self):
        values = ChannelValues.from_bgr([1, 2, 3])
        self.assertEqual((values.red, values.green, values.blue), (3, 2, 1))


if __name__ == "__main__":
    unittest.main()
