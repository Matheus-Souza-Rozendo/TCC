import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import cv2
import numpy as np

from calibracao_branco import lut_cli
from calibracao_branco.channels import ChannelValues
from calibracao_branco.color_classes import PixelClass, colored_fraction, maturity_from_fraction
from calibracao_branco.color_groups import DISCARD
from calibracao_branco.color_lut import load_lut
from calibracao_branco.gain_file import CalibrationResult, GainFileWriter
from calibracao_branco.labeled_capture import LabeledPhotoStore, TomatoLabels
from calibracao_branco.region import RegionOfInterest
from calibracao_branco.sampling import WhiteReferenceSample

REGION = RegionOfInterest(40, 40, 560, 400)
GREEN, ORANGE, RED, CALYX, HIGHLIGHT = (60, 170, 90), (40, 160, 235), (40, 40, 200), (25, 70, 25), (235, 235, 235)


def tomato_photo(maturity: str, variation: int) -> np.ndarray:
    random = np.random.default_rng(variation)
    image = np.clip(random.normal(14, 3, (480, 640, 3)), 0, 255).astype(np.uint8)
    center, radius = (320 + variation * 7, 240), 90
    if maturity == "imaturo":
        cv2.circle(image, center, radius, GREEN, -1)
        cv2.circle(image, center, 22, CALYX, -1)
    elif maturity == "intermediario":
        cv2.circle(image, center, radius, GREEN, -1)
        cv2.ellipse(image, center, (radius, radius), 0, -90, 90, ORANGE, -1)
    else:
        cv2.circle(image, center, radius, RED, -1)
        cv2.circle(image, (center[0] - 30, center[1] - 30), 10, HIGHLIGHT, -1)
    noise = random.normal(0, 4, image.shape)
    return np.clip(image + noise * (image > 30), 0, 255).astype(np.uint8)


def name_like_an_operator(groups) -> list:
    """Nomeia cada grupo pela cor do centro, como o operador faria olhando o painel."""
    names = []
    for lightness, a_axis, _ in groups.centers_lab:
        if lightness > 220:
            names.append(DISCARD)
        elif lightness < 90 and a_axis < 128:
            names.append(PixelClass.CALICE.label)
        elif a_axis > 165:
            names.append(PixelClass.VERMELHO.label)
        elif a_axis > 135:
            names.append(PixelClass.ROSADO.label)
        elif a_axis < 120:
            names.append(PixelClass.VERDE.label)
        else:
            names.append(PixelClass.AMARELADO.label)
    return names


class MaturityRuleTests(unittest.TestCase):
    def test_thresholds_of_rf02(self):
        self.assertEqual([maturity_from_fraction(f) for f in (0.05, 0.10, 0.60, 0.61)],
                         ["imaturo", "intermediario", "intermediario", "maduro"])

    def test_calyx_does_not_count_as_tomato_surface(self):
        class_map = np.array([[PixelClass.VERMELHO, PixelClass.VERDE, PixelClass.CALICE, PixelClass.CALICE]])
        self.assertAlmostEqual(colored_fraction(class_map, np.ones_like(class_map)), 0.5)


class LutGenerationEndToEndTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._folder = tempfile.TemporaryDirectory()
        root = Path(cls._folder.name)
        cls.gain_file, cls.dataset, cls.lut_file = root / "bancada.gain", root / "Dataset-cor", root / "lut_cor.npz"
        sample = WhiteReferenceSample(ChannelValues(200, 200, 200), ChannelValues(0.01, 0.01, 0.01), 30)
        GainFileWriter().write(CalibrationResult(ChannelValues(1, 1, 1), sample, REGION, "referencia_verde",
                                                 datetime(2026, 1, 1)), cls.gain_file)
        store = LabeledPhotoStore(cls.dataset)
        tomato_id = 0
        for maturity in ("imaturo", "intermediario", "maduro"):
            for variation in range(3):
                tomato_id += 1
                for photo in range(2):
                    store.save(tomato_photo(maturity, variation * 2 + photo),
                               TomatoLabels(tomato_id, frozenset(), maturity, None))
        captured_groups = []
        original_cluster = lut_cli.cluster_colors

        def capture_groups(*arguments):
            captured_groups.append(original_cluster(*arguments))
            return captured_groups[-1]

        with mock.patch.object(lut_cli, "cluster_colors", side_effect=capture_groups), \
                mock.patch.object(lut_cli, "_open_for_viewing"), \
                mock.patch.object(lut_cli, "_ask_group_names",
                                  side_effect=lambda *_: name_like_an_operator(captured_groups[-1])), \
                mock.patch("builtins.print"):
            cls.exit_code = lut_cli.main(["--gain", str(cls.gain_file), "--pasta", str(cls.dataset),
                                          "--saida", str(cls.lut_file)])
        cls.report = (cls.dataset / "lut" / "RELATORIO.md").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls._folder.cleanup()

    def test_runs_and_saves_everything(self):
        self.assertEqual(self.exit_code, 0)
        for produced in ("grupos.json", "grupos.png", "RELATORIO.md"):
            self.assertTrue((self.dataset / "lut" / produced).is_file(), produced)
        self.assertEqual(len(list((self.dataset / "lut" / "conferencia").iterdir())), 18)

    def test_lut_classifies_the_tomato_colors(self):
        lut = load_lut(self.lut_file)
        self.assertEqual(lut.shape, (256, 256, 256))
        self.assertEqual(lut[GREEN], PixelClass.VERDE)
        self.assertEqual(lut[RED], PixelClass.VERMELHO)
        self.assertEqual(lut[14, 14, 14], PixelClass.FUNDO)

    def test_every_photo_gets_the_informed_maturity(self):
        self.assertNotIn("**não**", self.report)
        self.assertIn("Tomates de validação", self.report)

    def test_rerun_reuses_saved_group_names(self):
        with mock.patch.object(lut_cli, "_ask_group_names") as ask, mock.patch("builtins.print"):
            exit_code = lut_cli.main(["--gain", str(self.gain_file), "--pasta", str(self.dataset),
                                      "--saida", str(self.lut_file)])
        self.assertEqual(exit_code, 0)
        ask.assert_not_called()


if __name__ == "__main__":
    unittest.main()
