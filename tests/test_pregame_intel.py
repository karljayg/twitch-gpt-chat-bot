"""Tests for core.pregame_intel (brief composition and known-opponent pre-game flow)."""
import unittest
from unittest.mock import MagicMock, patch

from settings import config

from core.pregame_intel import (
    PreGameBrief,
    abbreviated_grouped_build_string,
    _replay_summary_sanitize_for_inline_prompt,
    compose_last_meeting_user_message,
    compose_build_order_user_message,
    format_record_line,
    run_known_opponent_pregame,
    supplement_player_comments_from_db_row,
)


def _minimal_db_row(**overrides):
    base = {
        "Player1_Name": getattr(config, "SC2_PLAYER_ACCOUNTS", ["Streamer"])[0],
        "Player2_Name": "OpponentBob",
        "Player1_Race": "Terran",
        "Player2_Race": "Zerg",
        "Replay_Summary": "Game Duration: 10m 0s\nSome replay text.",
    }
    base.update(overrides)
    return base


class TestInlineReplaySanitize(unittest.TestCase):
    def test_strips_players_trained_timestamp_keeps_winners_duration(self):
        blob = (
            "Players: KJ: Zerg, Jtunn: Zerg Map: White Rabbit LE Region: us Game Type: 1v1 "
            "Timestamp: 1776874777 Winners: Jtunn Losers: KJ KJ trained: 1 Hatchery, 1 SpawningPool "
            "Jtunn trained: 5 Hatchery, 1 SpawningPool\n"
            "Game Duration: 22m 19s\n"
        )
        out = _replay_summary_sanitize_for_inline_prompt(blob)
        self.assertNotIn("Players:", out)
        self.assertNotIn("Timestamp:", out)
        self.assertNotIn("KJ trained:", out)
        self.assertNotIn("Jtunn trained:", out)
        self.assertIn("Winners:", out)
        self.assertIn("Game Duration", out)
        self.assertIn("Last game map from archive: White Rabbit LE", out)

    def test_strips_trained_without_colon(self):
        blob = "Winners: B Losers: A A trained extractor, drone B trained hatchery\nGame Duration: 1m\n"
        out = _replay_summary_sanitize_for_inline_prompt(blob)
        self.assertNotIn("extractor", out)
        self.assertNotIn("A trained", out)
        self.assertNotIn("B trained", out)

    def test_compose_inline_prompt_excludes_trained_noise(self):
        blob = (
            "Players: A: Zerg, B: Zerg Map: Foo LE Region: us Timestamp: 999 Winners: B Losers: A "
            "A trained: 1 Hatchery B trained: 2 Hatchery\nGame Duration: 5m 0s\n"
        )
        brief = PreGameBrief(
            opponent_display_name="B",
            opponent_race="Zerg",
            streamer_current_race="Zerg",
            streamer_race_compare="Zerg",
            today_streamer_race="Zerg",
            today_opponent_race="Zerg",
            db_result=_minimal_db_row(Replay_Summary=blob),
            how_long_ago="1 hour ago",
            record_vs=None,
            player_comments=[],
            first_few_build_steps=None,
            inline_saved_notes_in_last_meeting=True,
        )
        msg = compose_last_meeting_user_message(brief)
        self.assertNotIn("A trained:", msg)
        self.assertNotIn("B trained:", msg)
        # Replay Players: blob removed (distinct from FORBIDDEN line mentioning 'Players:').
        self.assertNotIn("Timestamp: 999", msg)
        self.assertNotIn("Region: us", msg)
        self.assertIn("[Last game map from archive: Foo LE]", msg)

    def test_strips_units_lost_tables(self):
        blob = (
            "Winners: KJ\nLosers: Kalhartt\nGame Duration: 6m 8s\n\n"
            "Units Lost by Kalhartt\nProbe: 4\nZealot: 11\nWarp Prism: 1\n\n"
            "Units Lost by KJ\nExtractor: 2\nDrone: 8\n"
        )
        out = _replay_summary_sanitize_for_inline_prompt(blob)
        self.assertNotIn("Units Lost by", out)
        self.assertNotIn("Warp Prism:", out)
        self.assertNotIn("Extractor:", out)
        self.assertIn("Winners:", out)
        self.assertIn("Game Duration", out)


class TestAbbreviatedGroupedBuild(unittest.TestCase):
    def test_pool_preserves_sequence_before_hatch(self):
        steps = [
            "Drone at 0:03",
            "Drone at 0:12",
            "SpawningPool at 0:22",
            "Drone at 0:25",
            "Hatchery at 0:45",
        ]
        out = abbreviated_grouped_build_string(steps)
        self.assertIn("Pool", out)
        ip = out.find("Pool")
        ih = out.find("Hatch")
        self.assertGreaterEqual(ip, 0)
        self.assertGreater(ih, ip)

    def test_coerces_name_upgrade_line_to_abbrev(self):
        steps = [
            "Drone at 0:01",
            "Time: 1:30, Name: Metabolic Boost, Supply: 28",
        ]
        out = abbreviated_grouped_build_string(steps)
        self.assertIn("Ling Speed", out)

    @patch.object(config, "PREGAME_OPENING_SUFFIX_MAX_GROUPS", 3, create=True)
    @patch.object(config, "PREGAME_OPENING_SUFFIX_MAX_CHARS", 0, create=True)
    def test_for_chat_suffix_caps_groups(self):
        steps = ["Drone at 0:01", "Pool at 0:20", "Hatch at 0:40", "Spine at 1:00"]
        out = abbreviated_grouped_build_string(steps, for_chat_suffix=True)
        self.assertTrue(out.endswith(" …"))
        self.assertLessEqual(out.count(","), 2)


class TestComposeLastMeeting(unittest.TestCase):
    def test_trivial_duration_override_branch(self):
        summ = "Game Duration: 45s\nWinners: X"
        brief = PreGameBrief(
            opponent_display_name="Bob",
            opponent_race="Zerg",
            streamer_current_race="Terran",
            streamer_race_compare="Terran",
            today_streamer_race="Terran",
            today_opponent_race="Zerg",
            db_result=_minimal_db_row(Replay_Summary=summ),
            how_long_ago="2 days ago",
            record_vs=None,
            player_comments=[],
            first_few_build_steps=None,
        )
        msg = compose_last_meeting_user_message(brief)
        self.assertIn("Very short prior game", msg)
        self.assertIn("45s", summ)
        self.assertNotIn("Do these 2", msg)

    def test_full_prompt_same_matchup(self):
        brief = PreGameBrief(
            opponent_display_name="Bob",
            opponent_race="Zerg",
            streamer_current_race="Terran",
            streamer_race_compare="Terran",
            today_streamer_race="Terran",
            today_opponent_race="Zerg",
            db_result=_minimal_db_row(),
            how_long_ago="a week ago",
            record_vs=None,
            player_comments=[],
            first_few_build_steps=None,
        )
        msg = compose_last_meeting_user_message(brief)
        self.assertIn("Do these 2", msg)
        self.assertIn(config.STREAMER_NICKNAME, msg)
        self.assertIn("RACE CONSTRAINT", msg)
        self.assertNotIn("{Map name}", msg)
        self.assertNotIn("{game duration}", msg)

    def test_prompt_fills_map_and_substitutes_streamer_alias(self):
        summ = (
            "Players: X vs Y Map: Echo LE Region: us Winners: wingingIt Losers: Bob\n"
            "Game Duration: 4m 39s\n"
        )
        brief = PreGameBrief(
            opponent_display_name="Bob",
            opponent_race="Zerg",
            streamer_current_race="Terran",
            streamer_race_compare="Terran",
            today_streamer_race="Terran",
            today_opponent_race="Zerg",
            db_result=_minimal_db_row(Replay_Summary=summ),
            how_long_ago="long ago",
            record_vs=None,
            player_comments=[],
            first_few_build_steps=None,
        )
        with patch.object(config, "SC2_PLAYER_ACCOUNTS", ["Streamer", "wingingIt"]):
            msg = compose_last_meeting_user_message(brief)
        self.assertIn("Echo LE", msg)
        self.assertIn("win for", msg.lower())
        self.assertNotIn("wingingIt", msg)
        self.assertNotIn("played the Zerg player Bob", msg)

    def test_uses_db_map_when_summary_map_missing(self):
        summ = (
            "Players: X vs Y Winners: Streamer Losers: Bob\n"
            "Game Duration: 5m 50s\n"
        )
        brief = PreGameBrief(
            opponent_display_name="Bob",
            opponent_race="Protoss",
            streamer_current_race="Terran",
            streamer_race_compare="Terran",
            today_streamer_race="Terran",
            today_opponent_race="Protoss",
            db_result=_minimal_db_row(Replay_Summary=summ, Map="Celestial Enclave LE"),
            how_long_ago="10 hours ago",
            record_vs=(1, 0),
            player_comments=[],
            first_few_build_steps=None,
        )
        msg = compose_last_meeting_user_message(brief)
        self.assertIn("on Celestial Enclave LE", msg)
        self.assertNotIn("on map", msg)

    def test_never_emits_map_placeholder_fallback(self):
        summ = "Winners: Streamer Losers: Bob\nGame Duration: 5m 50s\n"
        brief = PreGameBrief(
            opponent_display_name="Bob",
            opponent_race="Protoss",
            streamer_current_race="Terran",
            streamer_race_compare="Terran",
            today_streamer_race="Terran",
            today_opponent_race="Protoss",
            db_result=_minimal_db_row(Replay_Summary=summ, Map=""),
            how_long_ago="10 hours ago",
            record_vs=(1, 0),
            player_comments=[],
            first_few_build_steps=None,
        )
        msg = compose_last_meeting_user_message(brief)
        self.assertNotIn("the map named in the excerpt below", msg)

    def test_bundled_notes_omit_duplicate_time_and_map(self):
        summ = "Winners: Streamer Losers: Bob\nGame Duration: 5m 50s\n"
        brief = PreGameBrief(
            opponent_display_name="Chiewy",
            opponent_race="Protoss",
            streamer_current_race="Terran",
            streamer_race_compare="Terran",
            today_streamer_race="Terran",
            today_opponent_race="Protoss",
            db_result=_minimal_db_row(Replay_Summary=summ, Map="Celestial Enclave LE"),
            how_long_ago="10 hours ago",
            record_vs=(1, 0),
            player_comments=[],
            first_few_build_steps=None,
            inline_saved_notes_in_last_meeting=True,
        )
        msg = compose_last_meeting_user_message(
            brief,
            bundled_saved_notes=True,
            saved_notes_text="Chiewy went cannon (~10h ago, Celestial Enclave LE)",
        )
        fixed_line = msg.split("(These values are filled from the archive", 1)[0]
        self.assertIn("The last time", msg)
        self.assertNotIn("Chiewy Chiewy", msg)
        self.assertNotIn("about 10 hours ago", fixed_line)
        self.assertNotIn("on Celestial Enclave LE", fixed_line)
        self.assertIn("in 5m 50s", msg)
        self.assertNotIn("was,", msg)

    def test_bundled_notes_instructions_include_one_shot_and_at_most_one_sentence(self):
        summ = "Winners: Streamer Losers: Bob\nGame Duration: 5m 50s\n"
        brief = PreGameBrief(
            opponent_display_name="Chiewy",
            opponent_race="Protoss",
            streamer_current_race="Terran",
            streamer_race_compare="Terran",
            today_streamer_race="Terran",
            today_opponent_race="Protoss",
            db_result=_minimal_db_row(Replay_Summary=summ, Map="Celestial Enclave LE"),
            how_long_ago="10 hours ago",
            record_vs=(1, 0),
            player_comments=[],
            first_few_build_steps=None,
            inline_saved_notes_in_last_meeting=True,
        )
        msg = compose_last_meeting_user_message(
            brief,
            bundled_saved_notes=True,
            saved_notes_text="Chiewy went cannon (~10h ago, Celestial Enclave LE)",
        )
        self.assertIn("Add at most ONE short sentence", msg)
        self.assertIn("One-shot style example", msg)
        self.assertIn("The last time was a win for KJ in 5m 50s", msg)

    def test_run_known_opener_includes_order_profile_guidance(self):
        bot = MagicMock()
        bot.db = object()
        log = MagicMock()
        ctx = []
        brief = PreGameBrief(
            opponent_display_name="Link",
            opponent_race="Zerg",
            streamer_current_race="Terran",
            streamer_race_compare="Terran",
            today_streamer_race="Terran",
            today_opponent_race="Zerg",
            db_result=_minimal_db_row(Map="White Rabbit LE", Date_Played="2026-04-20 10:00:00"),
            how_long_ago="12 hours ago",
            record_vs=(17, 16),
            player_comments=[],
            first_few_build_steps=["Pool at 0:20"],
            inline_saved_notes_in_last_meeting=True,
        )
        with patch("core.pregame_intel.processMessageForOpenAI") as oai, \
             patch("core.pregame_intel.get_ml_analyzer") as gma, \
             patch("core.pregame_intel.msgToChannel"):
            gma.return_value = _ml_analyzer_mock(chat_returns=False, analysis_data=None)
            run_known_opponent_pregame(bot, brief, log, ctx, "MapX")
        prompt = oai.call_args[0][1]
        self.assertIn("Required opener facts (include each exactly once; order can vary)", prompt)
        self.assertIn("Order profile for this message:", prompt)
        self.assertIn("- ", prompt)


class TestFormatRecordLine(unittest.TestCase):
    def test_below_threshold(self):
        self.assertIsNone(format_record_line((1, 0), "Bob"))

    def test_at_threshold(self):
        line = format_record_line((2, 1), "Bob")
        self.assertIsNotNone(line)
        self.assertIn("2-1", line)
        self.assertIn("Bob", line)


class TestComposeBuildOrder(unittest.TestCase):
    def test_groups_duplicates(self):
        steps = ["Probe at 12", "Probe at 13", "Zealot at 22"]
        msg = compose_build_order_user_message("Alice", steps)
        self.assertIn("Opponent build focus", msg)
        self.assertIn("Probe x2", msg)


def _ml_analyzer_mock(chat_returns=True, analysis_data=None, analyze_side_effect=None):
    m = MagicMock()
    if analyze_side_effect is not None:
        m.analyze_opponent_for_chat.side_effect = analyze_side_effect
    else:
        m.analyze_opponent_for_chat.return_value = analysis_data
    m.generate_ml_analysis_message.return_value = chat_returns
    m._format_ml_chat_message.return_value = None
    return m


class TestRunKnownOpponentPregame(unittest.TestCase):
    def setUp(self):
        self.bot = MagicMock()
        self.bot.db = object()
        self.log = MagicMock()
        self.ctx = []

    @patch("core.pregame_intel.get_ml_analyzer")
    @patch("core.pregame_intel.twitch_notes_from_saved_comments", return_value="NOTE_LINE")
    @patch("core.pregame_intel.msgToChannel")
    def test_notes_last_meeting_only_skips_separate_build_llm(self, _mch, _notes_fn, gma):
        gma.return_value = _ml_analyzer_mock(
            chat_returns=False, analysis_data=None
        )
        comments = [{"date_played": "2024-01-01", "text": "x"}]
        brief = PreGameBrief(
            opponent_display_name="Bob",
            opponent_race="Zerg",
            streamer_current_race="Terran",
            streamer_race_compare="Terran",
            today_streamer_race="Terran",
            today_opponent_race="Zerg",
            db_result=_minimal_db_row(),
            how_long_ago="1 day ago",
            record_vs=None,
            player_comments=comments,
            first_few_build_steps=["Drone at 12"],
        )
        with patch("core.pregame_intel.processMessageForOpenAI") as oai:
            run_known_opponent_pregame(
                self.bot, brief, self.log, self.ctx, "MapX",
            )
            gma.return_value.analyze_opponent_for_chat.assert_called_once()
            gma.return_value.generate_ml_analysis_message.assert_not_called()
            # Formatted saved notes → last-meeting only; no second OpenAI for DB build extract.
            self.assertEqual(oai.call_count, 1)
        _mch.assert_called()

    @patch("core.pregame_intel.get_ml_analyzer")
    @patch("core.pregame_intel.processMessageForOpenAI")
    @patch("core.pregame_intel.msgToChannel")
    def test_no_comments_runs_ml_then_last_meeting(self, mch, oai, gma):
        learning = {
            "opponent_name": "Bob",
            "analysis_type": "learning_data",
            "total_games": 3,
            "win_rate": 0.4,
            "top_strategies": [("roach", 2)],
            "recent_comments": ["a", "b"],
        }
        gma.return_value = _ml_analyzer_mock(chat_returns=True, analysis_data=learning)
        brief = PreGameBrief(
            opponent_display_name="Bob",
            opponent_race="Zerg",
            streamer_current_race="Terran",
            streamer_race_compare="Terran",
            today_streamer_race="Terran",
            today_opponent_race="Zerg",
            db_result=_minimal_db_row(),
            how_long_ago="1 day ago",
            record_vs=None,
            player_comments=[],
            first_few_build_steps=["Drone at 12"],
        )
        run_known_opponent_pregame(self.bot, brief, self.log, self.ctx, "MapX")
        gma.return_value.generate_ml_analysis_message.assert_called_once()
        # ML success sets ml_analysis_ran — build-from-DB line is skipped (same as game_started).
        oai.assert_called_once()
        mch.assert_not_called()

    @patch("core.pregame_intel.get_ml_analyzer")
    @patch("core.pregame_intel.processMessageForOpenAI")
    @patch("core.pregame_intel.msgToChannel")
    def test_ml_failure_allows_build_order_message(self, mch, oai, gma):
        gma.return_value = _ml_analyzer_mock(analyze_side_effect=RuntimeError("ml off"))
        brief = PreGameBrief(
            opponent_display_name="Bob",
            opponent_race="Zerg",
            streamer_current_race="Terran",
            streamer_race_compare="Terran",
            today_streamer_race="Terran",
            today_opponent_race="Zerg",
            db_result=_minimal_db_row(),
            how_long_ago="1 day ago",
            record_vs=None,
            player_comments=[],
            first_few_build_steps=["Drone at 12"],
        )
        run_known_opponent_pregame(self.bot, brief, self.log, self.ctx, "MapX")
        self.assertEqual(oai.call_count, 1)
        suf = oai.call_args.kwargs.get("response_suffix") or ""
        self.assertIn("opening:", suf)
        self.assertIn("Drone", suf)
        mch.assert_not_called()

    @patch("core.pregame_intel.get_ml_analyzer")
    @patch("core.pregame_intel.processMessageForOpenAI")
    @patch("core.pregame_intel.msgToChannel")
    def test_quiet_no_build_skips_glhf(self, mch, _oai, gma):
        gma.return_value = _ml_analyzer_mock(chat_returns=False, analysis_data=None)
        brief = PreGameBrief(
            opponent_display_name="Bob",
            opponent_race="Zerg",
            streamer_current_race="Terran",
            streamer_race_compare="Terran",
            today_streamer_race="Terran",
            today_opponent_race="Zerg",
            db_result=_minimal_db_row(),
            how_long_ago="1 day ago",
            record_vs=None,
            player_comments=[],
            first_few_build_steps=None,
        )
        run_known_opponent_pregame(
            self.bot, brief, self.log, self.ctx, "MapX",
            quiet_when_no_build_extract=True,
        )
        for call in mch.call_args_list:
            args = call[0]
            if len(args) >= 2 and isinstance(args[1], str):
                self.assertNotIn("GLHF", args[1])

    @patch.object(config, "PREGAME_SEND_SEPARATE_GLHF_LINE", True, create=True)
    @patch("core.pregame_intel.get_ml_analyzer")
    @patch("core.pregame_intel.processMessageForOpenAI")
    @patch("core.pregame_intel.msgToChannel")
    def test_live_glhf_when_no_build_not_quiet(self, mch, oai, gma):
        gma.return_value = _ml_analyzer_mock(chat_returns=False, analysis_data=None)
        brief = PreGameBrief(
            opponent_display_name="Bob",
            opponent_race="Zerg",
            streamer_current_race="Protoss",
            streamer_race_compare="Protoss",
            today_streamer_race="Protoss",
            today_opponent_race="Zerg",
            db_result=_minimal_db_row(),
            how_long_ago="1 day ago",
            record_vs=None,
            player_comments=[],
            first_few_build_steps=None,
        )
        run_known_opponent_pregame(
            self.bot, brief, self.log, self.ctx, "MapX",
            quiet_when_no_build_extract=False,
        )
        oai.assert_called()
        phrase = getattr(config, "PREGAME_GLHF_PHRASE", "GLHFGG")
        glhf_calls = [
            c
            for c in mch.call_args_list
            if len(c[0]) >= 2 and (phrase in str(c[0][1]) or "GLHF" in str(c[0][1]))
        ]
        self.assertEqual(len(glhf_calls), 1)

    @patch("core.pregame_intel.get_ml_analyzer")
    @patch("core.pregame_intel.twitch_notes_from_saved_comments", return_value="NOTE_LINE")
    @patch("core.pregame_intel.msgToChannel")
    @patch("core.pregame_intel.processMessageForOpenAI")
    def test_inline_preview_skips_build_appendix_when_saved_notes(self, oai, _mch, _notes, gma):
        gma.return_value = _ml_analyzer_mock(chat_returns=False, analysis_data=None)
        comments = [{"date_played": "2024-01-01", "text": "x"}]
        brief = PreGameBrief(
            opponent_display_name="Bob",
            opponent_race="Zerg",
            streamer_current_race="Terran",
            streamer_race_compare="Terran",
            today_streamer_race="Terran",
            today_opponent_race="Zerg",
            db_result=_minimal_db_row(),
            how_long_ago="1 day ago",
            record_vs=None,
            player_comments=comments,
            first_few_build_steps=["Drone at 12"],
            inline_saved_notes_in_last_meeting=True,
        )
        self.bot.db = None
        run_known_opponent_pregame(self.bot, brief, self.log, self.ctx, "MapX")
        self.assertEqual(oai.call_count, 1)
        combined = oai.call_args[0][1]
        self.assertIn("NOTE_LINE", combined)
        # Saved notes present — opener must not duplicate DB replay build (expert text is source of truth).
        self.assertNotIn("=== Opponent opening", combined)

    @patch("core.pregame_intel.get_ml_analyzer")
    @patch("core.pregame_intel.processMessageForOpenAI")
    @patch("core.pregame_intel.msgToChannel")
    def test_inline_preview_includes_build_when_no_saved_notes(self, _mch, oai, gma):
        gma.return_value = _ml_analyzer_mock(chat_returns=False, analysis_data=None)
        brief = PreGameBrief(
            opponent_display_name="Bob",
            opponent_race="Zerg",
            streamer_current_race="Terran",
            streamer_race_compare="Terran",
            today_streamer_race="Terran",
            today_opponent_race="Zerg",
            db_result=_minimal_db_row(),
            how_long_ago="1 day ago",
            record_vs=None,
            player_comments=[],
            first_few_build_steps=["Drone at 12"],
            inline_saved_notes_in_last_meeting=True,
        )
        self.bot.db = None
        run_known_opponent_pregame(self.bot, brief, self.log, self.ctx, "MapX")
        combined = oai.call_args[0][1]
        self.assertNotIn("=== Opponent opening", combined)
        suffix = oai.call_args.kwargs.get("response_suffix", "")
        self.assertIn("Bob opening:", suffix)
        self.assertIn("Drone", suffix)

    @patch("core.pregame_intel.get_ml_analyzer")
    @patch("core.pregame_intel.twitch_notes_from_saved_comments", return_value="")
    @patch("core.pregame_intel.processMessageForOpenAI")
    def test_inline_empty_formatted_notes_but_strong_pattern_skips_build_appendix(self, oai, _notes, gma):
        pattern = {
            "opponent_name": "Bob",
            "analysis_type": "pattern_matching",
            "matched_patterns": [{"similarity": 0.9, "comment": "hydra timing"}],
            "build_order_preview": [{"name": "Drone"}],
            "player_comments_text": "",
        }
        gma.return_value = _ml_analyzer_mock(chat_returns=False, analysis_data=pattern)
        comments = [{"date_played": "2024-01-01", "text": "x"}]
        brief = PreGameBrief(
            opponent_display_name="Bob",
            opponent_race="Zerg",
            streamer_current_race="Terran",
            streamer_race_compare="Terran",
            today_streamer_race="Terran",
            today_opponent_race="Zerg",
            db_result=_minimal_db_row(),
            how_long_ago="1 day ago",
            record_vs=None,
            player_comments=comments,
            first_few_build_steps=["Drone at 12"],
            inline_saved_notes_in_last_meeting=True,
        )
        run_known_opponent_pregame(self.bot, brief, self.log, self.ctx, "MapX")
        self.assertEqual(oai.call_count, 1)
        combined = oai.call_args[0][1]
        self.assertNotIn("=== Opponent opening", combined)


class TestSupplementPlayerComments(unittest.TestCase):
    def test_inserts_primary_row_comment_when_missing_from_query(self):
        db_row = {
            "Player_Comments": "2 base immortal all in",
            "Map": "Foo LE",
            "Date_Played": None,
        }
        out = supplement_player_comments_from_db_row(db_row, [])
        self.assertEqual(len(out), 1)
        self.assertIn("immortal", out[0]["player_comments"])

    def test_skips_when_comment_text_already_present(self):
        db_row = {"Player_Comments": "same note", "Map": "X"}
        existing = [{"player_comments": "same note"}]
        out = supplement_player_comments_from_db_row(db_row, existing)
        self.assertEqual(len(out), 1)


if __name__ == "__main__":
    unittest.main()
