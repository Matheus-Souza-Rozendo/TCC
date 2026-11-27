import unittest

from calibracao_branco.wilson_interval import WilsonInterval


class WilsonIntervalTest(unittest.TestCase):
    def test_nine_of_ten_matches_published_value(self):
        interval = WilsonInterval.for_proportion(9, 10)
        self.assertAlmostEqual(interval.lower, 0.5958, places=3)
        self.assertAlmostEqual(interval.upper, 0.9821, places=3)

    def test_zero_successes_has_lower_bound_zero(self):
        interval = WilsonInterval.for_proportion(0, 10)
        self.assertEqual(interval.lower, 0.0)
        self.assertAlmostEqual(interval.upper, 0.2775, places=3)

    def test_all_successes_has_upper_bound_one(self):
        self.assertEqual(WilsonInterval.for_proportion(22, 22).upper, 1.0)

    def test_empty_sample_is_rejected(self):
        with self.assertRaises(ValueError):
            WilsonInterval.for_proportion(0, 0)


if __name__ == "__main__":
    unittest.main()
