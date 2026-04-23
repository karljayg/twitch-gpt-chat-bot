"""Tests for last_time_played response cleanup in api.chat_utils."""
import unittest
from datetime import datetime, timedelta

from api.chat_utils import (
    _apply_last_time_style_variation,
    _collapse_duplicate_played_name,
    _fold_map_time_recap_into_last_time_sentence,
    _fuse_last_time_with_strategy_sentence,
    _normalize_last_time_grammar,
    _relative_when,
    _reorder_last_time_segments,
    _strip_duplicate_strategy_and_map_tail,
    _strip_redundant_last_time_fact_recap,
    _strip_llm_opponent_opening_clause,
    _strip_last_time_prompt_leaks,
    _truncate_last_time_twitch_total,
    _vary_record_sentence_wording,
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


class TestRelativeWhen(unittest.TestCase):
    def test_same_day_uses_hours_not_today(self):
        dt = datetime.now() - timedelta(hours=10)
        out = _relative_when(dt)
        self.assertEqual(out, "10h ago")


class TestLastTimeRecapDedupe(unittest.TestCase):
    def test_collapse_duplicate_played_name(self):
        s = "The last time KJ played Chiewy Chiewy was about 10 hours ago."
        out = _collapse_duplicate_played_name(s)
        self.assertEqual(out, "The last time KJ played Chiewy was about 10 hours ago.")

    def test_strip_redundant_fact_recap_sentence(self):
        s = (
            "The last time was a loss for KJ in 20m 5s. "
            "Theyve been on Taito Citadel LE, with a game duration of 20 minutes and 5 seconds, "
            "and the winner was IIIllIlllIIl."
        )
        out = _strip_redundant_last_time_fact_recap(s)
        self.assertEqual(out, "The last time was a loss for KJ in 20m 5s.")

    def test_fuse_strategy_and_last_time_sentence(self):
        s = (
            "KJ is 1-4 vs IIIllIlllIIl. IIIllIlllIIl went oracle, sentry to prism at choke drop, collosus (~10h ago, Taito Citadel LE). "
            "The last time was a win for IIIllIlllIIl in 20m 5s."
        )
        out = _fuse_last_time_with_strategy_sentence(s)
        self.assertRegex(
            out,
            r"(which was|and that was|so that was|Last game was) a win for IIIllIlllIIl in 20m 5s",
        )

    def test_fold_map_time_recap_into_last_time_sentence(self):
        s = (
            "The last time a win for KJ in 8m 31s. "
            "They've been on White Rabbit LE about 12 hours ago, with KJ winning."
        )
        out = _fold_map_time_recap_into_last_time_sentence(s)
        self.assertIn("on White Rabbit LE", out)
        self.assertIn("about 12 hours ago", out)
        self.assertNotIn("They've been on", out)

    def test_strip_short_recap_after_fused_sentence(self):
        s = (
            "KJ is 17-16 vs Link, who went 15 pool speedling bane, to roach follow up, all in (~12h ago, White Rabbit LE), "
            "which was a win for KJ in 8m 31s. "
            "Theyve been on White Rabbit LE about 12 hours ago, with KJ winning."
        )
        out = _strip_redundant_last_time_fact_recap(s)
        self.assertNotIn("Theyve been on White Rabbit LE about 12 hours ago", out)

    def test_normalize_was_artifact(self):
        s = "which was a win for KJ was in 8m 31s."
        out = _normalize_last_time_grammar(s)
        self.assertEqual(out, "which was a win for KJ in 8m 31s.")

    def test_normalize_was_artifact_without_in(self):
        s = "and that was a win for KJ was 8m 31s."
        out = _normalize_last_time_grammar(s)
        self.assertEqual(out, "and that was a win for KJ in 8m 31s.")

    def test_strip_duplicate_strategy_and_map_tail(self):
        s = (
            "KJ is 0-1 vs Meteor, and they went marine to blueflame hellion tanks banshee in their Most recent game "
            "about 1 day ago, so that was a loss for KJ in 12 minutes 40 seconds on White Rabbit LE. "
            "Meteor usually goes marine to blueflame hellion tanks banshee. "
            "Theyve been on White Rabbit LE recently."
        )
        out = _strip_duplicate_strategy_and_map_tail(s)
        self.assertNotIn("Meteor usually goes marine to blueflame hellion tanks banshee.", out)
        self.assertNotIn("Theyve been on White Rabbit LE recently.", out)

    def test_reorder_last_time_segments_preserves_all_core_parts(self):
        s = (
            "KJ is 1-4 vs IIIllIlllIIl. "
            "IIIllIlllIIl went oracle to colossus. "
            "The last time was a loss for KJ in 20m 5s."
        )
        out = _reorder_last_time_segments(s)
        self.assertIn("1-4", out)
        self.assertIn("went oracle to colossus", out)
        self.assertIn("loss for KJ in 20m 5s", out)

    def test_vary_record_sentence_wording(self):
        s = "KJ is 17-16 vs Link. Link went pool bane."
        out = _vary_record_sentence_wording(s)
        self.assertIn("17-16", out)
        self.assertIn("Link", out)

    def test_apply_style_variation_keeps_core_facts(self):
        s = "The last time was a win for KJ in 8m 31s on White Rabbit LE about 12 hours ago."
        out = _apply_last_time_style_variation(s)
        self.assertIn("win for KJ in 8m 31s", out)
        self.assertIn("White Rabbit LE", out)
        self.assertIn("12 hours ago", out)
        self.assertNotEqual(out, "")


if __name__ == "__main__":
    unittest.main()
