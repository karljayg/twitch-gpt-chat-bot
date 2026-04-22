"""Tests for compact build preview formatting and staged matching helpers."""
import unittest

from utils.sc2_abbreviations import format_build_order_for_chat
from api.ml_opponent_analyzer import MLOpponentAnalyzer


class TestBuildPreviewFormatting(unittest.TestCase):
    def test_groups_consecutive_supply_and_unit(self):
        steps = [
            {"supply": 12, "name": "SpawningPool", "time": 40},
            {"supply": 11, "name": "Drone", "time": 43},
            {"supply": 11, "name": "Drone", "time": 45},
            {"supply": 14, "name": "Extractor", "time": 62},
            {"supply": 13, "name": "Zergling", "time": 78},
            {"supply": 13, "name": "Zergling", "time": 80},
            {"supply": 13, "name": "Zergling", "time": 81},
        ]
        text = format_build_order_for_chat(steps, max_items=12, show_workers=2)
        self.assertIn("12 Pool", text)
        self.assertIn("11 Drone x2", text)
        self.assertIn("13 Ling x3", text)


class TestStagedMatchingHelpers(unittest.TestCase):
    def test_slice_build_window_respects_early_cutoff(self):
        analyzer = MLOpponentAnalyzer()
        steps = [
            {"name": "Drone", "supply": 12, "time": 10},
            {"name": "SpawningPool", "supply": 12, "time": 35},
            {"name": "Extractor", "supply": 14, "time": 70},
            {"name": "Lair", "supply": 40, "time": 280},
            {"name": "HydraliskDen", "supply": 55, "time": 320},
        ]
        early = analyzer._slice_build_window(  # pylint: disable=protected-access
            steps, max_steps=30, max_time=240, max_supply=50
        )
        self.assertEqual(len(early), 3)
        self.assertEqual(early[-1]["name"], "Extractor")


if __name__ == "__main__":
    unittest.main()
