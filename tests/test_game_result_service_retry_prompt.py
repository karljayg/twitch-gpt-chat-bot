"""Retry prompt composition tests for game_result_service."""
import unittest

from core.game_result_service import _compose_retry_commentary_line, _retry_prompt_flags


class TestComposeRetryCommentaryLine(unittest.TestCase):
    def test_appends_followup_when_commentary_present(self):
        line, appended = _compose_retry_commentary_line(
            "KJ wins quick in 5:50 on Celestial Enclave LE, with what looked like cannon to proxy gateway robo immortal."
        )
        self.assertTrue(appended)
        self.assertIn("Your one-line take on their build?", line)
        self.assertEqual(line.count("?"), 1)

    def test_empty_commentary_disables_inline_followup(self):
        line, appended = _compose_retry_commentary_line("   ")
        self.assertFalse(appended)
        self.assertEqual(line, "")

    def test_retry_prompt_flags_when_followup_inline(self):
        flags = _retry_prompt_flags(True)
        self.assertTrue(flags["suppress_followup_prompt"])
        self.assertFalse(flags["force_followup_prompt"])
        self.assertTrue(flags["suppress_pattern_validation_line"])

    def test_retry_prompt_flags_when_followup_not_inline(self):
        flags = _retry_prompt_flags(False)
        self.assertFalse(flags["suppress_followup_prompt"])
        self.assertTrue(flags["force_followup_prompt"])
        self.assertFalse(flags["suppress_pattern_validation_line"])


if __name__ == "__main__":
    unittest.main()
