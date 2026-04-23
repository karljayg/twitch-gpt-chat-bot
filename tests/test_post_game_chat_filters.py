"""Post-game Twitch line filtering (strategy summary + ML deterministic message)."""
import unittest

from api.ml_opponent_analyzer import MLOpponentAnalyzer
from api.chat_utils import summarize_strategy_with_units, sanitize_retry_replay_commentary


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


class TestRetryReplayCommentarySanitizer(unittest.TestCase):
    def test_keeps_one_sentence(self):
        s = (
            "KJ took it in under 6, with what looks like cannon to proxy gateway robo immortal build on Celestial Enclave LE. "
            "Extra sentence that should be dropped."
        )
        out = sanitize_retry_replay_commentary(s, max_words=50)
        self.assertNotIn("Extra sentence", out)
        self.assertTrue(out.endswith("."))

    def test_trims_word_count(self):
        s = " ".join(["word"] * 40)
        out = sanitize_retry_replay_commentary(s, max_words=10)
        self.assertLessEqual(len(out.split()), 11)  # 10 + possible ellipsis token

    def test_avoids_dangling_to_after_trim(self):
        s = (
            "Ggs KJ, Jötunn took the win on White Rabbit LE in about 22 minutes "
            "with what looks like a 3 hatch ling bane to muta."
        )
        out = sanitize_retry_replay_commentary(s, max_words=16)
        self.assertFalse(out.lower().endswith(" to."))
        self.assertFalse(out.lower().endswith(" into."))
        self.assertTrue(out.endswith("."))


if __name__ == "__main__":
    unittest.main()
