import csv
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from calibracao_branco import labeled_capture_cli
from calibracao_branco.labeled_capture import (LabeledPhotoStore, TomatoLabels, parse_defects, parse_maturity,
                                               parse_optional_diameter)
from calibracao_branco.preview import CalibrationPreview
from calibracao_branco.region import RegionOfInterest

FRAME = np.full((120, 160, 3), 30, np.uint8)
KEY_SPACE, KEY_ENTER, KEY_ESCAPE, NO_KEY = 32, 13, 27, 255


def read_rows(root: Path):
    with (root / "rotulos.csv").open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file, delimiter=";"))


class LabelParsingTests(unittest.TestCase):
    def test_several_defect_letters_in_any_order(self):
        self.assertEqual(parse_defects("pR"), {"podre", "rachado"})

    def test_empty_defects_means_healthy(self):
        self.assertTrue(TomatoLabels(1, parse_defects(""), None, None).is_healthy())

    def test_unknown_defect_letter_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_defects("rx")

    def test_maturity_is_optional(self):
        self.assertIsNone(parse_maturity(""))
        self.assertEqual(parse_maturity("3"), "maduro")

    def test_diameter_accepts_decimal_comma_and_rejects_absurd_values(self):
        self.assertEqual(parse_optional_diameter("27,5"), 27.5)
        with self.assertRaises(ValueError):
            parse_optional_diameter("275")


class LabeledPhotoStoreTests(unittest.TestCase):
    def setUp(self):
        self._folder = tempfile.TemporaryDirectory()
        self.root = Path(self._folder.name) / "Dataset-proprio"
        self.store = LabeledPhotoStore(self.root)

    def tearDown(self):
        self._folder.cleanup()

    def test_first_tomato_is_number_one(self):
        self.assertEqual(self.store.next_tomato_id(), 1)

    def test_photos_of_same_tomato_are_numbered_in_sequence(self):
        labels = TomatoLabels(1, frozenset({"rachado"}), "maduro", 24.3)
        first, second = self.store.save(FRAME, labels), self.store.save(FRAME, labels)
        self.assertEqual((first.name, second.name), ("tomate_0001_foto_01.jpg", "tomate_0001_foto_02.jpg"))
        self.assertEqual(self.store.next_tomato_id(), 2)

    def test_csv_row_has_one_column_per_defect_and_excel_decimal(self):
        self.store.save(FRAME, TomatoLabels(7, frozenset({"rachado", "mancha"}), None, 24.3))
        row = read_rows(self.root)[0]
        self.assertEqual((row["rachado"], row["mancha"], row["podre"], row["sadio"]), ("1", "1", "0", "0"))
        self.assertEqual((row["diametro_paquimetro_mm"], row["maturacao"]), ("24,30", ""))

    def test_header_is_written_only_once(self):
        for tomato_id in (1, 2):
            self.store.save(FRAME, TomatoLabels(tomato_id, frozenset(), None, None))
        self.assertEqual([row["tomate"] for row in read_rows(self.root)], ["1", "2"])


class FakeCamera:
    def __init__(self, address):
        pass

    def read_frame(self):
        return FRAME.copy()

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exception_info):
        pass


class CaptureSessionTests(unittest.TestCase):
    def test_full_session_with_two_tomatoes(self):
        typed_answers = ["rp", "3", "26,1",  # tomate 1: rachado + podre, maduro, 26,1 mm
                         "x", "", "", "",    # tomate 2: letra inválida, depois sadio
                         "sair"]
        keys = [NO_KEY, KEY_SPACE, KEY_SPACE, KEY_ENTER,  # tomate 1: 2 fotos
                KEY_SPACE, KEY_ESCAPE]                   # tomate 2: 1 foto e encerra
        with tempfile.TemporaryDirectory() as folder, \
                mock.patch("builtins.input", side_effect=typed_answers), \
                mock.patch.object(CalibrationPreview, "show_and_read_key", side_effect=keys), \
                mock.patch.object(CalibrationPreview, "close_windows"), \
                mock.patch.object(labeled_capture_cli, "OpenCvCameraAdapter", FakeCamera), \
                mock.patch.object(labeled_capture_cli.GainFileReader, "read_region",
                                  return_value=RegionOfInterest(10, 10, 100, 80)), \
                mock.patch.object(labeled_capture_cli.GainFileReader, "read_camera_address", return_value="0"), \
                mock.patch("builtins.print"):
            exit_code = labeled_capture_cli.main(["--pasta", folder])
            rows = read_rows(Path(folder))
            photos = sorted(path.name for path in (Path(folder) / "fotos").iterdir())
        self.assertEqual(exit_code, 0)
        self.assertEqual(photos, ["tomate_0001_foto_01.jpg", "tomate_0001_foto_02.jpg", "tomate_0002_foto_01.jpg"])
        self.assertEqual([(r["tomate"], r["rachado"], r["podre"], r["sadio"]) for r in rows],
                         [("1", "1", "1", "0"), ("1", "1", "1", "0"), ("2", "0", "0", "1")])


if __name__ == "__main__":
    unittest.main()
