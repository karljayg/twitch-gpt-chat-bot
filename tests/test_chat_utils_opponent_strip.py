"""Tests for last_time_played response cleanup in api.chat_utils."""
import unittest

from api.chat_utils import (
    _strip_llm_opponent_opening_clause,
    _strip_last_time_prompt_leaks,
    _truncate_last_time_twitch_total,
)


class TestStripLlmOpponentOpening(unittest.TestCase):
    def test_strips_mid_message_clause(self):
        s = (
            "Last time was fast. Opponent opening: Hatchery, Pool, Ling x6. "
            "More text should go if we strip from Opponent opening."
        )
        out = _strip_llm_opponent_opening_clause(s)
        self.assertEqual(out, "Last time was fast.")

    def test_strips_leading_clause(self):
        s = "Opponent opening: Drone, Pool"
        out = _strip_llm_opponent_opening_clause(s)
        self.assertEqual(out, "")

    def test_case_insensitive(self):
        s = "Hi opponent OPENING: foo"
        out = _strip_llm_opponent_opening_clause(s)
        self.assertEqual(out, "Hi")


class TestStripPromptLeaks(unittest.TestCase):
    def test_removes_appended_after_reply_instruction(self):
        s = (
            "Last meet was fine. The opponent opening is appended after your reply as a verbatim ordered line "
            "from the DB build extract (same order as training steps). Do NOT describe opponent units, buildings, "
            "or training order from the replay excerpt in your message. Wittykitty opening: Drone"
        )
        out = _strip_last_time_prompt_leaks(s)
        self.assertNotIn("appended after your reply", out)
        self.assertNotIn("DB build extract", out)
        self.assertNotIn("Do NOT describe opponent units", out)
        self.assertIn("Last meet was fine.", out)


class TestTruncateLastTime(unittest.TestCase):
    def test_noop_under_limit(self):
        self.assertEqual(_truncate_last_time_twitch_total("short", 100), "short")

    def test_adds_etc_when_long(self):
        long_line = " ".join(["word"] * 80)
        out = _truncate_last_time_twitch_total(long_line, 80)
        self.assertTrue(out.endswith(" [etc]"))
        self.assertLessEqual(len(out), 80)


if __name__ == "__main__":
    unittest.main()
