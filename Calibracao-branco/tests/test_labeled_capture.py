import csv
import tempfile
import tkinter as tk
import unittest
from pathlib import Path

import numpy as np

from calibracao_branco.capture_controller import CaptureController, LabelChoice
from calibracao_branco.capture_destinations import (ColorDestinationStrategy, DefectDestinationStrategy,
                                                    TestDestinationStrategy)
from calibracao_branco.labeled_capture import LabeledPhotoStore, TomatoLabels, parse_optional_diameter
from calibracao_branco.region import RegionOfInterest

FRAME = np.full((120, 160, 3), 30, np.uint8)
RIPE = LabelChoice(defects=frozenset(), maturity="maduro", diameter_text="")


def read_rows(dataset_folder: Path):
    with (dataset_folder / "rotulos.csv").open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file, delimiter=";"))


class DiameterParsingTests(unittest.TestCase):
    def test_accepts_decimal_comma_and_empty(self):
        self.assertEqual(parse_optional_diameter("27,5"), 27.5)
        self.assertIsNone(parse_optional_diameter(" "))

    def test_rejects_text_and_absurd_values_with_clear_message(self):
        for text in ("abc", "275"):
            with self.assertRaisesRegex(ValueError, "Diâmetro"):
                parse_optional_diameter(text)


class LabeledPhotoStoreTests(unittest.TestCase):
    def setUp(self):
        self._folder = tempfile.TemporaryDirectory()
        self.root = Path(self._folder.name) / "Dataset-proprio"

    def tearDown(self):
        self._folder.cleanup()

    def test_photos_go_to_the_subfolder_of_the_rule_and_csv_keeps_the_relative_path(self):
        store = LabeledPhotoStore(self.root, lambda labels: "sadio" if labels.is_healthy() else "com_defeito")
        saved = store.save(FRAME, TomatoLabels(3, frozenset({"rachado"}), None, 24.3))
        self.assertEqual(saved, self.root / "fotos" / "com_defeito" / "tomate_0003_foto_01.jpg")
        row = read_rows(self.root)[0]
        self.assertEqual((row["arquivo"], row["rachado"], row["sadio"]), ("com_defeito/tomate_0003_foto_01.jpg", "1", "0"))
        self.assertEqual(row["diametro_paquimetro_mm"], "24,30")
        self.assertTrue(store.labeled_photos()[0].path.is_file())

    def test_photos_of_same_tomato_are_numbered_in_sequence(self):
        store = LabeledPhotoStore(self.root)
        labels = TomatoLabels(1, frozenset(), "maduro", None)
        names = [store.save(FRAME, labels).name for _ in range(2)]
        self.assertEqual(names, ["tomate_0001_foto_01.jpg", "tomate_0001_foto_02.jpg"])
        self.assertEqual(store.next_tomato_id(), 2)


class CaptureControllerTests(unittest.TestCase):
    def setUp(self):
        self._folder = tempfile.TemporaryDirectory()
        self.root = Path(self._folder.name)
        self.controller = CaptureController(self.root)

    def tearDown(self):
        self._folder.cleanup()

    def test_color_destination_separates_by_maturity(self):
        saved = self.controller.take_photo(FRAME, RIPE)
        self.assertEqual(saved.parent, self.root / "Dataset-cor" / "fotos" / "maduro")

    def test_color_destination_requires_maturity(self):
        with self.assertRaisesRegex(ValueError, "maturação"):
            self.controller.take_photo(FRAME, LabelChoice(frozenset(), None, ""))

    def test_defect_destination_separates_healthy_and_defective(self):
        self.controller.select_destination(DefectDestinationStrategy())
        healthy = self.controller.take_photo(FRAME, LabelChoice(frozenset(), None, ""))
        self.controller.start_new_tomato()
        defective = self.controller.take_photo(FRAME, LabelChoice(frozenset({"podre"}), None, ""))
        self.assertEqual((healthy.parent.name, defective.parent.name), ("sadio", "com_defeito"))
        self.assertEqual(healthy.parents[2], self.root / "Dataset-proprio")

    def test_labels_are_locked_after_first_photo(self):
        self.controller.take_photo(FRAME, RIPE)
        second = self.controller.take_photo(FRAME, LabelChoice(frozenset({"podre"}), "imaturo", ""))
        self.assertEqual(second.parent.name, "maduro")
        self.assertEqual(self.controller.photos_of_tomato, 2)
        with self.assertRaises(ValueError):
            self.controller.select_destination(TestDestinationStrategy())

    def test_new_tomato_gets_next_number_of_its_own_dataset(self):
        self.controller.take_photo(FRAME, RIPE)
        self.controller.start_new_tomato()
        self.assertEqual(self.controller.tomato_id, 2)
        self.controller.select_destination(DefectDestinationStrategy())
        self.assertEqual(self.controller.tomato_id, 1)
        self.controller.select_destination(ColorDestinationStrategy())
        self.assertEqual(self.controller.tomato_id, 2)

    def test_test_destination_keeps_all_photos_together(self):
        self.controller.select_destination(TestDestinationStrategy())
        saved = self.controller.take_photo(FRAME, LabelChoice(frozenset({"mancha"}), "intermediario", "22,1"))
        self.assertEqual(saved.parent, self.root / "Dataset-teste" / "fotos")


class FakeFeed:
    def preview(self, display_width):
        return np.zeros((90, display_width, 3), np.uint8)

    def photo(self):
        return FRAME.copy()


class CaptureWindowSmokeTest(unittest.TestCase):
    """Monta a janela de verdade e simula os cliques (sem abrir o laço de eventos)."""

    def setUp(self):
        try:
            tk.Tk().destroy()
        except tk.TclError:
            self.skipTest("sem tela disponível para o Tk")
        from calibracao_branco.capture_gui import CaptureWindow
        self._folder = tempfile.TemporaryDirectory()
        self.root = Path(self._folder.name)
        self.window = CaptureWindow(FakeFeed(), CaptureController(self.root), display_width=160)

    def tearDown(self):
        self.window._root.destroy()
        self._folder.cleanup()

    def test_click_photo_without_maturity_shows_error_then_saves_after_choosing(self):
        self.window._on_take_photo()
        self.assertIn("maturação", self.window._status.cget("text"))
        self.window._maturity.set("imaturo")
        self.window._on_take_photo()
        self.assertTrue((self.root / "Dataset-cor" / "fotos" / "imaturo" / "tomate_0001_foto_01.jpg").is_file())
        self.assertIn("Foto salva", self.window._status.cget("text"))

    def test_labels_are_disabled_after_photo_and_enabled_on_new_tomato(self):
        self.window._maturity.set("maduro")
        self.window._on_take_photo()
        self.assertTrue(self.window._label_widgets[0].instate(["disabled"]))
        self.window._on_new_tomato()
        self.assertFalse(self.window._label_widgets[0].instate(["disabled"]))
        self.assertEqual(self.window._tomato_text.cget("text"), "Tomate nº 2")

    def test_video_frame_is_shown(self):
        self.window._refresh_video()
        self.assertEqual(self.window._frame_image.width(), 160)


if __name__ == "__main__":
    unittest.main()
