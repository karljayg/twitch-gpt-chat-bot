"""Post-game Twitch line filtering (strategy summary + ML deterministic message)."""
import unittest

from api.ml_opponent_analyzer import MLOpponentAnalyzer
from api.chat_utils import summarize_strategy_with_units


class TestSummarizeStrategyWithUnits(unittest.TestCase):
    def test_units_only_without_pattern_emits_nothing(self):
        self.assertEqual(
            summarize_strategy_with_units(
                "Pierce",
                "",
                ["Gateway", "CyberneticsCore", "Zealot"],
                is_winner=False,
                similarity=0.5,
            ),
            "",
        )

    def test_units_with_strong_pattern_allowed(self):
        s = summarize_strategy_with_units(
            "Pierce",
            "charge all in",
            ["Gateway", "Zealot"],
            is_winner=False,
            similarity=0.9,
        )
        self.assertIn("Pattern:", s)
        self.assertIn("Gateway", s)


class TestFormatMlChatMessage(unittest.TestCase):
    def test_pattern_matching_weak_labels_only_skips_chat(self):
        az = MLOpponentAnalyzer()
        data = {
            "opponent_name": "Pierce",
            "opponent_race": "Protoss",
            "analysis_type": "pattern_matching",
            "matched_patterns": [
                {"similarity": 0.45, "comment": "weak label"},
            ],
            "build_order_preview": [
                {"name": "Probe"},
                {"name": "Pylon"},
            ],
            "player_comments_text": "",
        }
        self.assertIsNone(az._format_ml_chat_message(data))

    def test_pattern_matching_strong_label_includes_extract(self):
        az = MLOpponentAnalyzer()
        data = {
            "opponent_name": "Pierce",
            "opponent_race": "Protoss",
            "analysis_type": "pattern_matching",
            "matched_patterns": [
                {"similarity": 0.92, "comment": "4 gate blink"},
            ],
            "build_order_preview": [
                {"name": "Probe"},
                {"name": "Pylon"},
            ],
            "player_comments_text": "",
        }
        text = az._format_ml_chat_message(data)
        self.assertIsNotNone(text)
        self.assertIn("Closest saved labels", text)
        self.assertIn("saved build extract", text)


if __name__ == "__main__":
    unittest.main()
