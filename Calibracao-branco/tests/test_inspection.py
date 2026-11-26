import csv
import tempfile
import tkinter as tk
import unittest
from pathlib import Path

import cv2
import numpy as np

from calibracao_branco.binary_metrics import BinaryMetrics
from calibracao_branco.channels import ChannelValues
from calibracao_branco.color_classes import PixelClass
from calibracao_branco.defect_classifier import DefectVerdict, MissingModelDefectClassifierNullObject
from calibracao_branco.inspection_overlay import InspectionOverlay
from calibracao_branco.inspection_session import InspectionSession
from calibracao_branco.maturity_classifier import LutMaturityClassifier, MissingLutMaturityClassifierNullObject
from calibracao_branco.pixel_scale import CellScale, GridSize, PixelScaleMap, RegionGrid
from calibracao_branco.region import RegionOfInterest
from calibracao_branco.segmentation import SegmentedObject, tomato_segmenter
from calibracao_branco.tomato_crops import CROP_SIZE_PX, crop_around
from calibracao_branco.tomato_inspection import (InspectionModels, SortingDestination, TomatoInspectionFacade)

FRAME_SHAPE = (300, 400, 3)
REGION = RegionOfInterest(20, 20, 360, 260)
MM_PER_PIXEL = 0.2
RED_TOMATO = (30, 30, 200)
GREEN_TOMATO = (40, 170, 60)
UNIT_GAINS = ChannelValues(1.0, 1.0, 1.0)


def scene(tomatoes) -> np.ndarray:
    """Fundo preto com ruído e elipses (tomates "grape") de cor, centro e semi-eixos dados."""
    rng = np.random.default_rng(1)
    frame = np.clip(np.full(FRAME_SHAPE, 20.0) + rng.normal(0, 3, FRAME_SHAPE), 0, 255).astype(np.uint8)
    for color, center, axes in tomatoes:
        cv2.ellipse(frame, center, axes, 0, 0, 360, color, -1)
    return frame


def uniform_scale_map() -> PixelScaleMap:
    grid = RegionGrid(REGION, GridSize(columns=2, rows=2))
    return PixelScaleMap(grid, [CellScale(cell, MM_PER_PIXEL, 10, 0.0, 0.0) for cell in grid.cells()])


def red_vs_green_lut() -> np.ndarray:
    """LUT de teste: vermelho forte = vermelho, verde forte = verde, resto = fundo."""
    blue, green, red = np.meshgrid(np.arange(256), np.arange(256), np.arange(256), indexing="ij")
    lut = np.full((256, 256, 256), PixelClass.FUNDO, np.uint8)
    lut[(red > 120) & (green < 100)] = PixelClass.VERMELHO
    lut[(green > 120) & (red < 100)] = PixelClass.VERDE
    return lut


class AlwaysDefectiveClassifier:
    def classify(self, crop_bgr):
        return DefectVerdict(True, 0.9)


def facade_with(defect_classifier=MissingModelDefectClassifierNullObject()) -> TomatoInspectionFacade:
    return TomatoInspectionFacade(InspectionModels(UNIT_GAINS, uniform_scale_map(),
                                                   LutMaturityClassifier(red_vs_green_lut()), defect_classifier))


class TomatoSegmentationTests(unittest.TestCase):
    def test_object_on_border_is_reported_and_not_inspected(self):
        frame = scene([(RED_TOMATO, (150, 150), (30, 22)), ((230, 230, 230), (375, 150), (20, 20))])
        result = tomato_segmenter().find_objects(frame, REGION)
        self.assertEqual((len(result.inside), result.touching_border_count), (1, 1))

    def test_empty_scene_is_not_an_error(self):
        self.assertEqual(tomato_segmenter().find_objects(scene([]), REGION).inside, [])

    def test_crop_is_square_with_tomato_in_the_middle_even_near_the_photo_edge(self):
        frame = scene([(RED_TOMATO, (35, 150), (14, 10))])
        tomato = tomato_segmenter().find_objects(frame, RegionOfInterest(0, 0, 400, 300)).inside[0]
        crop = crop_around(frame, tomato)
        self.assertEqual(crop.shape, (CROP_SIZE_PX, CROP_SIZE_PX, 3))
        self.assertGreater(crop[CROP_SIZE_PX // 2, CROP_SIZE_PX // 2, 2], 150)


class InspectionFacadeTests(unittest.TestCase):
    def test_size_in_mm_of_an_elongated_tomato(self):
        report = facade_with().inspect(scene([(RED_TOMATO, (150, 150), (60, 45))]))
        size = report.tomatoes[0].size
        self.assertAlmostEqual(size.length_mm, 120 * MM_PER_PIXEL, delta=0.6)
        self.assertAlmostEqual(size.width_mm, 90 * MM_PER_PIXEL, delta=0.6)
        self.assertAlmostEqual(size.diameter_mm, 2 * np.sqrt(60 * 45) * MM_PER_PIXEL, delta=0.4)
        self.assertLess(size.circularity, 1.0)

    def test_destination_by_maturity_and_defect_goes_to_discard(self):
        frame = scene([(RED_TOMATO, (100, 100), (30, 22)), (GREEN_TOMATO, (280, 200), (30, 22))])
        healthy = facade_with().inspect(frame)
        self.assertEqual([t.destination() for t in healthy.tomatoes],
                         [SortingDestination.MADURO, SortingDestination.IMATURO])
        defective = facade_with(AlwaysDefectiveClassifier()).inspect(frame)
        self.assertEqual({t.destination() for t in defective.tomatoes}, {SortingDestination.DESCARTE})

    def test_without_lut_the_tomato_has_no_class_but_is_still_measured(self):
        models = InspectionModels(UNIT_GAINS, uniform_scale_map(), MissingLutMaturityClassifierNullObject(),
                                  MissingModelDefectClassifierNullObject())
        tomato = TomatoInspectionFacade(models).inspect(scene([(RED_TOMATO, (150, 150), (30, 22))])).tomatoes[0]
        self.assertEqual((tomato.destination(), tomato.maturity.label(), tomato.defect.label()),
                         (SortingDestination.INDEFINIDO, "sem LUT", "sem CNN"))
        self.assertGreater(tomato.size.diameter_mm, 0)

    def test_overlay_shows_only_the_region_with_margin(self):
        facade = facade_with()
        report = facade.inspect(scene([(RED_TOMATO, (150, 150), (30, 22))]))
        view = InspectionOverlay(facade.region).draw(report)
        self.assertEqual(view.shape[:2], (300, 400))  # região + 30 px de margem, limitada à foto


class InspectionSessionTests(unittest.TestCase):
    def test_counts_and_csv_log_with_decimal_comma(self):
        with tempfile.TemporaryDirectory() as folder:
            session = InspectionSession(Path(folder))
            frame = scene([(RED_TOMATO, (100, 100), (30, 22)), (GREEN_TOMATO, (280, 200), (30, 22))])
            session.register(facade_with().inspect(frame))
            session.register(facade_with().inspect(frame))
            self.assertEqual((session.total(), session.counts[SortingDestination.MADURO]), (4, 2))
            with session.log_file.open(encoding="utf-8-sig", newline="") as file:
                rows = list(csv.DictReader(file, delimiter=";"))
            self.assertEqual([(r["classificacao"], r["tomate"]) for r in rows], [("1", "1"), ("1", "2"),
                                                                              ("2", "1"), ("2", "2")])
            self.assertIn(",", rows[0]["diametro_mm"])
            session.reset_counts()
            self.assertEqual(session.total(), 0)


class BinaryMetricsTests(unittest.TestCase):
    def test_metrics_with_defect_as_positive(self):
        metrics = BinaryMetrics.from_labels(np.array([0, 0, 0, 1, 1]), np.array([0, 0, 1, 1, 0]))
        self.assertEqual((metrics.true_negatives, metrics.false_positives, metrics.false_negatives,
                          metrics.true_positives), (2, 1, 1, 1))
        self.assertAlmostEqual(metrics.recall(), 0.5)
        self.assertAlmostEqual(metrics.specificity(), 2 / 3)
        self.assertAlmostEqual(metrics.balanced_accuracy(), (0.5 + 2 / 3) / 2)


class FakeCamera:
    def read_frame(self):
        return scene([(RED_TOMATO, (100, 100), (30, 22)), (GREEN_TOMATO, (280, 200), (30, 22))])


class InspectionWindowSmokeTest(unittest.TestCase):
    """Monta a IHM de verdade e simula os cliques (sem abrir o laço de eventos)."""

    def setUp(self):
        try:
            tk.Tk().destroy()
        except tk.TclError:
            self.skipTest("sem tela disponível para o Tk")
        from calibracao_branco.inspection_gui import InspectionSetup, InspectionWindow
        self._folder = tempfile.TemporaryDirectory()
        setup = InspectionSetup(facade_with(), InspectionSession(Path(self._folder.name)), True, False)
        self.window = InspectionWindow(FakeCamera(), setup)

    def tearDown(self):
        self.window.root.destroy()
        self._folder.cleanup()

    def test_classify_fills_cards_counters_and_table(self):
        self.window._on_classify()
        self.assertEqual(self.window._history.row_count(), 2)
        self.assertEqual(len(self.window._cards.winfo_children()), 2)
        self.assertTrue(self.window._session.log_file.is_file())

    def test_live_and_continuous_video_frames_are_shown(self):
        self.window._refresh_video()
        self.window._toggle_continuous()
        self.window._refresh_video()
        self.assertGreater(self.window._frame_image.width(), 0)

    def test_reset_clears_table(self):
        self.window._on_classify()
        self.window._on_reset()
        self.assertEqual(self.window._history.row_count(), 0)


if __name__ == "__main__":
    unittest.main()
