"""Tests for OpponentAnalysisService brief race fields."""
# pylint: disable=protected-access
import unittest
from unittest.mock import MagicMock, patch

from core.opponent_analysis_service import OpponentAnalysisService


def _db_row(**overrides):
    row = {
        "Player1_Name": "StreamerLadder",
        "Player2_Name": "OpponentBob",
        "Player1_PickRace": "Terran",
        "Player2_PickRace": "Zerg",
        "Date_Played": "2026-01-01 00:00:00",
        "Replay_Summary": "Winners: StreamerLadder\nGame Duration: 10m",
    }
    row.update(overrides)
    return row


class TestOpponentAnalysisServiceRaceFields(unittest.TestCase):
    @patch("core.opponent_analysis_service.run_known_opponent_pregame")
    @patch("core.opponent_analysis_service.replay_h2h_streamer_vs_opponent", return_value=None)
    @patch("core.opponent_analysis_service.parse_streamer_record_vs_opponent", return_value=None)
    @patch("core.opponent_analysis_service.calculate_time_ago", return_value="1 day ago")
    @patch("core.opponent_analysis_service.config.SC2_PLAYER_ACCOUNTS", ["StreamerLadder"], create=True)
    def test_today_streamer_race_uses_current_game_race(
        self, _time_ago, _parse_record, _replay_h2h, run_pregame
    ):
        db = MagicMock()
        db.get_player_records.return_value = []
        db.extract_opponent_build_order.return_value = ["Drone at 0:12"]
        db.get_player_comments.return_value = []
        svc = OpponentAnalysisService(db=db, twitch_bot=MagicMock())

        ok = svc._analyze_known_opponent(
            opponent_name="OpponentBob",
            opponent_race="Zerg",
            streamer_race="Protoss",
            current_map="MapX",
            db_result=_db_row(Player1_PickRace="Terran"),
            context_history=[],
        )

        self.assertTrue(ok)
        brief = run_pregame.call_args[0][1]
        self.assertEqual(brief.streamer_race_compare, "Terran")
        self.assertEqual(brief.today_streamer_race, "Protoss")

    @patch("core.opponent_analysis_service.run_known_opponent_pregame")
    @patch("core.opponent_analysis_service.replay_h2h_streamer_vs_opponent", return_value=None)
    @patch("core.opponent_analysis_service.parse_streamer_record_vs_opponent", return_value=None)
    @patch("core.opponent_analysis_service.calculate_time_ago", return_value="2 days ago")
    @patch("core.opponent_analysis_service.config.SC2_PLAYER_ACCOUNTS", ["StreamerLadder"], create=True)
    def test_random_opponent_keeps_today_race_and_marks_random_opponent(
        self, _time_ago, _parse_record, _replay_h2h, run_pregame
    ):
        db = MagicMock()
        db.get_player_records.return_value = []
        db.get_player_comments.return_value = []
        svc = OpponentAnalysisService(db=db, twitch_bot=MagicMock())

        ok = svc._analyze_known_opponent(
            opponent_name="OpponentBob",
            opponent_race="Zerg",
            streamer_race="Random",
            current_map="MapY",
            db_result=_db_row(Player1_PickRace="Terran"),
            context_history=[],
            random_race_intel=(("Protoss", _db_row(), [], []),),
        )

        self.assertTrue(ok)
        brief = run_pregame.call_args[0][1]
        self.assertEqual(brief.today_streamer_race, "Random")
        self.assertEqual(brief.opponent_race, "Random")
        self.assertEqual(brief.today_opponent_race, "Random")


if __name__ == "__main__":
    unittest.main()
