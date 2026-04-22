"""pregame_matchup_blurb: FSL vs replay-archive one-liners for replay-summary prep."""
import unittest
from unittest.mock import MagicMock, patch

from core.pregame_matchup_blurb import (
    _dedupe_name_hints,
    build_dual_player_tidbit,
    build_streamer_vs_opponent_tidbit,
    fsl_career_maps_sentence,
    replay_archive_head_to_head_totals,
    replay_archive_head_to_head_totals_multi,
    resolve_fsl_real_name,
)


class _DbBothFsl:
    def fsl_player_by_name_exact(self, name: str):
        if name.lower() == "alice":
            return {"Real_Name": "AliceFSL"}
        if name.lower() == "bob":
            return {"Real_Name": "BobFSL"}
        return None

    def fsl_players_search(self, q: str, limit: int = 40):
        return {}

    def fsl_matches_h2h(self, player_name: str, opponent_name: str, season=None):
        assert player_name == "AliceFSL" and opponent_name == "BobFSL"
        return {
            "h2h": {
                "series_total": 4,
                "maps_won_a": 11,
                "maps_won_b": 9,
            }
        }

    def get_head_to_head_matchup(self, a, b):
        raise AssertionError("should not need replay when FSL works")


class _DbReplayOnly:
    def fsl_player_by_name_exact(self, name: str):
        return None

    def fsl_players_search(self, q: str, limit: int = 40):
        return {"players": []}

    def fsl_matches_h2h(self, player_name: str, opponent_name: str, season=None):
        return {"h2h": {}}

    def get_head_to_head_matchup(self, a, b):
        return [
            f"{a} (Terran) vs {b} (Zerg), 3 wins - 1 wins",
            f"{a} (Protoss) vs {b} (Zerg), 2 wins - 4 wins",
        ]


class TestBuildDualPlayerTidbit(unittest.TestCase):
    @patch("core.pregame_matchup_blurb._fsl_commands_enabled", return_value=True)
    def test_fsl_when_both_resolve(self, _en):
        s = build_dual_player_tidbit(_DbBothFsl(), "Alice", "Bob")
        self.assertIsNotNone(s)
        self.assertIn("FSL", s)
        self.assertIn("11-9", s)
        self.assertIn("Alice", s)
        self.assertIn("Bob", s)

    @patch("core.pregame_matchup_blurb._fsl_commands_enabled", return_value=True)
    def test_replay_when_not_fsl(self, _en):
        s = build_dual_player_tidbit(_DbReplayOnly(), "X", "Y")
        self.assertEqual(s, "X is 5-5 vs Y.")


class TestStreamerVsOpponent(unittest.TestCase):
    @patch("settings.config.STREAMER_NICKNAME", "Sn")
    @patch("core.pregame_matchup_blurb._streamer_name_hints", return_value=("Sn", "SnAcct"))
    @patch("core.pregame_matchup_blurb._fsl_commands_enabled", return_value=True)
    def test_streamer_fsl_maps(self, _en, _hints):
        class D:
            def fsl_player_by_name_exact(self, name: str):
                nl = name.lower()
                if nl == "sn":
                    return {"Real_Name": "SnFSL"}
                if nl == "opp":
                    return {"Real_Name": "OppFSL"}
                return None

            def fsl_players_search(self, q: str, limit: int = 40):
                return {}

            def fsl_matches_h2h(self, player_name: str, opponent_name: str, season=None):
                return {"h2h": {"series_total": 1, "maps_won_a": 2, "maps_won_b": 1}}

            def get_head_to_head_matchup(self, a, b):
                return []

        s = build_streamer_vs_opponent_tidbit(D(), "Opp", ("opp",))
        self.assertIsNotNone(s)
        self.assertIn("Sn", s)
        self.assertIn("2-1", s)
        self.assertIn("Opp", s)


class TestReplayMultiHints(unittest.TestCase):
    def test_second_opponent_hint_matches(self):
        class D:
            def get_head_to_head_matchup(self, a, b):
                if a == "S" and b == "Wrong":
                    return []
                if a == "S" and b == "Right":
                    return ["S (T) vs Right (Z), 2 wins - 1 wins"]
                return []

        tot = replay_archive_head_to_head_totals_multi(D(), ["S"], ["Wrong", "Right"])
        self.assertEqual(tot, (2, 1))


class TestAsciiFoldHints(unittest.TestCase):
    def test_dedupe_adds_folded_spelling(self):
        names = _dedupe_name_hints(["Jötunn"])
        self.assertIn("Jotunn", names)


class TestHelpers(unittest.TestCase):
    def test_replay_totals_none(self):
        db = MagicMock()
        db.get_head_to_head_matchup.return_value = []
        self.assertIsNone(replay_archive_head_to_head_totals(db, "a", "b"))

    def test_fsl_sentence_none_empty_row(self):
        db = MagicMock()
        db.fsl_matches_h2h.return_value = {"h2h": {"series_total": 0}}
        self.assertIsNone(
            fsl_career_maps_sentence(db, "A", "B", "qa", "qb"),
        )

    @patch("core.pregame_matchup_blurb._fsl_commands_enabled", return_value=False)
    def test_resolve_disabled(self, _en):
        db = MagicMock()
        self.assertIsNone(resolve_fsl_real_name(db, "Anyone"))
