"""
FSL @-ask scenario matrix: natural-language-style prompts → router action → `_exec_action`.

These tests validate **execution + formatting** with a mock DB (no HTTP, no LLM). They do **not**
prove the router LLM picks the right JSON; add golden-router tests separately if needed.

Human spot-check (you confirm facts against live DB): use the same question text with `fsl …`
commands or API while deployed.

Run:
  pytest tests/test_fsl_nl_scenario_matrix.py -v > tmp_pytest_fsl_nl.txt 2>&1
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from core.fsl_natural_language import (
    FslAskAssistant,
    _solo_h2h_aggregate_plan_from_question,
    _solo_h2h_plan_from_question,
    _team_roster_plan_from_question,
)


class MockLLM:
    """Unused for exec-only tests."""

    async def generate_raw(self, prompt: str) -> str:
        return "{}"


class MockFslDb:
    """Minimal payloads so formatters succeed."""

    def fsl_players_search(self, q: str, limit: int = 40) -> Dict[str, Any]:
        return {
            "players": [
                {
                    "Player_ID": 1,
                    "Real_Name": "Night",
                    "Team_Name": "Team Alpha",
                }
            ]
        }

    def fsl_player_by_name_exact(self, name: str) -> Dict[str, Any]:
        return {
            "Player_ID": 99,
            "Real_Name": name.strip() or "Atlantis",
            "Team_Name": "Psi Storm",
        }

    def fsl_player_by_id(self, player_id: int) -> Dict[str, Any]:
        return {
            "Player_ID": int(player_id),
            "Team_Name": "Psi Storm",
            "Championship_Record": "Major bracket 1st",
            "TeamLeague_Championship_Record": "Team league S9 finalist",
        }

    def fsl_team_league_season_summary(self, season: int) -> Dict[str, Any]:
        return {
            "summary": {
                "season": int(season),
                "schedule_rows": 8,
                "standings_leader_names": ["PulledTheBoys"],
                "standings_tie_at_top": False,
                "last_week_number": 8,
                "champion_from_final_week_match": "PulledTheBoys",
                "standings": [
                    {"team_name": "PulledTheBoys", "wins": 6, "losses": 1},
                    {"team_name": "Angry Space Hares", "wins": 5, "losses": 2},
                ],
            }
        }

    def fsl_solo_division_season_standings(
        self, season: int, division: str
    ) -> Dict[str, Any]:
        _ = division
        return {
            "summary": {
                "season": int(season),
                "division_t_code": "S",
                "division_label": "Code S",
                "match_row_count": 20,
                "interpretation_note": "test",
                "official_champion_from_players_record": {
                    "player_id": 501,
                    "player_name": "Winner",
                    "championship_record": '{"season":5,"division":"Code S","title":"champion"}',
                },
                "second_place_player_names": ["RunnerUp"],
                "standings": [
                    {"rank": 1, "player_name": "Winner", "wins": 10, "losses": 1},
                    {"rank": 2, "player_name": "RunnerUp", "wins": 9, "losses": 2},
                ],
            }
        }

    def fsl_teams_search(self, q: str, limit: int = 40) -> Dict[str, Any]:
        return {
            "teams": [
                {
                    "Team_ID": 10,
                    "Team_Name": "Alpha Squad",
                    "Status": "Active",
                }
            ]
        }

    def fsl_team_by_id(self, team_id: int) -> Dict[str, Any]:
        return {
            "Team_ID": int(team_id),
            "Team_Name": "Alpha Squad",
            "Status": "Active",
            "TeamLeague_Championship_Record": "2-1",
            "Captain_ID": 5,
            "Co_Captain_ID": 6,
        }

    def fsl_schedule(
        self,
        season: Any = None,
        week: Any = None,
        limit: int = 120,
    ) -> Dict[str, Any]:
        return {
            "schedule": [
                {
                    "season": season or 11,
                    "week_number": week or 1,
                    "team1_name": "Team A",
                    "team2_name": "Team B",
                    "team1_score": 3,
                    "team2_score": 2,
                    "winner_team_name": "Team A",
                    "match_date": "2026-04-01",
                }
            ]
        }

    def fsl_matches(
        self,
        season: Any = None,
        player_name: Any = None,
        player_id: Any = None,
        opponent_name: Any = None,
        limit: int = 60,
    ) -> Dict[str, Any]:
        return {
            "matches": [
                {
                    "winner_name": "Foo",
                    "loser_name": "Bar",
                    "map_win": 2,
                    "map_loss": 1,
                    "season": season or 10,
                    "fsl_match_id": 5001,
                },
                {
                    "winner_name": "Bar",
                    "loser_name": "Foo",
                    "map_win": 2,
                    "map_loss": 0,
                    "season": season or 10,
                    "fsl_match_id": 5002,
                },
            ]
        }

    def fsl_matches_h2h(
        self,
        player_name: str,
        opponent_name: str,
        season: Any = None,
    ) -> Dict[str, Any]:
        return {
            "h2h": {
                "player_a_query": player_name,
                "player_b_query": opponent_name,
                "season_filter": int(season) if season is not None else None,
                "series_total": 2,
                "series_wins_a": 1,
                "series_wins_b": 1,
                "maps_won_a": 3,
                "maps_won_b": 3,
                "first_match_id": 1,
                "last_match_id": 2,
                "next_series_win_prob_a": 0.5,
                "next_series_win_prob_b": 0.5,
                "empirical_model": "laplace_series_record",
                "empirical_note": "test",
            }
        }

    def fsl_leaderboard_match_win_pct(
        self, min_matches: int = 10, limit: int = 15
    ) -> Dict[str, Any]:
        return {
            "leaderboard": [
                {
                    "Player_ID": 40,
                    "Real_Name": "Leader",
                    "wins": 30,
                    "losses": 10,
                    "matches_played": 40,
                    "win_pct": 0.75,
                }
            ]
        }

    def fsl_leaderboard_match_total_wins(
        self, min_matches: int = 1, limit: int = 15
    ) -> Dict[str, Any]:
        return {
            "leaderboard": [
                {
                    "Player_ID": 7,
                    "Real_Name": "WinLord",
                    "wins": 100,
                    "losses": 20,
                    "matches_played": 120,
                    "win_pct": 0.83,
                }
            ]
        }

    def fsl_leaderboard_maps_won(self, limit: int = 15) -> Dict[str, Any]:
        return {
            "leaderboard": [
                {
                    "Player_ID": 101,
                    "Real_Name": "Dpoo",
                    "total_maps_w": 166,
                    "total_maps_l": 128,
                },
                {
                    "Player_ID": 1,
                    "Real_Name": "Neutrophil",
                    "total_maps_w": 127,
                    "total_maps_l": 62,
                },
                {
                    "Player_ID": 2,
                    "Real_Name": "DarkMenace",
                    "total_maps_w": 127,
                    "total_maps_l": 55,
                },
            ]
        }

    def fsl_team_players(self, team_id: int) -> Dict[str, Any]:
        return {
            "players": [
                {
                    "Player_ID": 5,
                    "Real_Name": "Captain Carl",
                    "Status": "Active",
                    "roster_role": "captain",
                },
                {
                    "Player_ID": 6,
                    "Real_Name": "CoCap Kim",
                    "Status": "Active",
                    "roster_role": "co_captain",
                },
                {
                    "Player_ID": 9,
                    "Real_Name": "Member Mo",
                    "Status": "Active",
                    "roster_role": "member",
                },
            ]
        }

    def fsl_match_by_id(self, fsl_match_id: int) -> Dict[str, Any]:
        return {
            "fsl_match_id": int(fsl_match_id),
            "winner_name": "Freeedom",
            "loser_name": "SirMalagant",
            "winner_race": "T",
            "loser_race": "P",
            "map_win": 2,
            "map_loss": 0,
            "season": 99,
        }

    def fsl_statistics_for_player(self, player_id: int) -> Dict[str, Any]:
        return {
            "statistics": [
                {
                    "Division": "Premier",
                    "Race": "Protoss",
                    "MapsW": 100,
                    "MapsL": 40,
                    "SetsW": 40,
                    "SetsL": 18,
                }
            ]
        }


# --- ≥20 distinct viewer intents → expected router action + params ---
# `natural_language` is what you would paste after @bot for a manual router smoke test.

EXEC_MATRIX: List[Dict[str, Any]] = [
    {
        "natural_language": "Find / spell players matching Night",
        "action": "players_search",
        "params": {"q": "Night", "limit": 8},
        "expect_substrings": ("FSL players", "Night"),
    },
    {
        "natural_language": "Who is Random guy in FSL search",
        "action": "players_search",
        "params": {"q": "Random"},
        "expect_substrings": ("FSL players",),
    },
    {
        "natural_language": "Atlantis career FSL stats maps and sets",
        "action": "player_detail",
        "params": {"name": "Atlantis"},
        "expect_substrings": ("Atlantis", "FSL stats", "Premier", "Championship record"),
    },
    {
        "natural_language": "Tell me about Alpha Squad team league row",
        "action": "team_detail",
        "params": {"name": "Alpha"},
        "expect_substrings": ("Alpha Squad", "Captain / co-captain"),
    },
    {
        "natural_language": "Who are the members of PulledTheBoys",
        "action": "team_roster",
        "params": {"name": "Pulled"},
        "expect_substrings": ("roster", "Captain Carl", "member"),
    },
    {
        "natural_language": "Who has the most series wins in FSL history",
        "action": "leaderboard_total_wins",
        "params": {"min_matches": 1, "limit": 15},
        "expect_substrings": ("series wins", "WinLord", "100"),
    },
    {
        "natural_language": "Who has the most map wins / games won (FSL_STATISTICS)",
        "action": "leaderboard_maps_won",
        "params": {"limit": 15},
        "expect_substrings": ("SUM(MapsW)", "Neutrophil", "127", "DarkMenace", "Dpoo"),
    },
    {
        "natural_language": "Teams matching psi substring",
        "action": "teams_search",
        "params": {"q": "psi"},
        "expect_substrings": ("FSL teams",),
    },
    {
        "natural_language": "FSL team league schedule season 11",
        "action": "schedule",
        "params": {"season": 11, "week": None},
        "expect_substrings": ("Team-league schedule", "Team A", "winner="),
    },
    {
        "natural_language": "Week 4 season 9 schedule games",
        "action": "schedule",
        "params": {"season": 9, "week": 4},
        "expect_substrings": ("Team-league schedule",),
    },
    {
        "natural_language": "Recent solo league matches involving Foo",
        "action": "matches",
        "params": {"player_name": "Foo", "season": None},
        "expect_substrings": ("FSL matches", "Foo"),
    },
    {
        "natural_language": "What is Foo record in season 10 (same path as PulledTheBoys + season)",
        "action": "matches",
        "params": {"player_name": "Foo", "season": 10},
        "expect_substrings": ("match record", "season 10"),
    },
    {
        "natural_language": "Darkmenace vs NukLeo head to head",
        "action": "matches",
        "params": {"player_name": "Darkmenace", "opponent_name": "NukLeo"},
        "expect_substrings": ("Head-to-head",),
    },
    {
        "natural_language": "Overall record Cyan vs LittleReaper career",
        "action": "matches_h2h",
        "params": {"player_name": "Cyan", "opponent_name": "LittleReaper"},
        "expect_substrings": ("Series record", "Maps won", "LittleReaper"),
    },
    {
        "natural_language": "Dark vs Light season 9 only H2H",
        "action": "matches",
        "params": {
            "player_name": "Dark",
            "opponent_name": "Light",
            "season": 9,
        },
        "expect_substrings": ("Head-to-head",),
    },
    {
        "natural_language": "Highest career series win percentage all time",
        "action": "leaderboard_win_pct",
        "params": {"min_matches": 10, "limit": 15},
        "expect_substrings": ("win %", "Leader"),
    },
    {
        "natural_language": "Top winrates min 20 games played",
        "action": "leaderboard_win_pct",
        "params": {"min_matches": 20, "limit": 10},
        "expect_substrings": ("Leader",),
    },
    {
        "natural_language": "Details for fsl_match_id 99001",
        "action": "match_detail",
        "params": {"match_id": 99001},
        "expect_substrings": ("99001", "Freeedom"),
    },
    {
        "natural_language": "FSL_STATISTICS rows for Player_ID 42",
        "action": "statistics_player",
        "params": {"player_id": 42},
        "expect_substrings": ("player_id 42", "Premier"),
    },
    {
        "natural_language": "Who won team league season 10 champion",
        "action": "team_league_season",
        "params": {"season": 10},
        "expect_substrings": ("Season 10", "PulledTheBoys", "Standings rank"),
    },
    {
        "natural_language": "Who was 2nd place Code S player in season 5",
        "action": "solo_division_season",
        "params": {"season": 5, "division": "Code S"},
        "expect_substrings": (
            "Season 5",
            "Code S",
            "Players.Championship_Record",
            "Second place player",
            "RunnerUp",
        ),
    },
    {
        "natural_language": "Full schedule tail default window",
        "action": "schedule",
        "params": {"season": None, "week": None},
        "expect_substrings": ("Team-league schedule",),
    },
    {
        "natural_language": "Career division race breakdown ZergMain",
        "action": "player_detail",
        "params": {"name": "ZergMain"},
        "expect_substrings": ("FSL stats",),
    },
    {
        "natural_language": "Foo last games no season filter",
        "action": "matches",
        "params": {"player_name": "Foo"},
        "expect_substrings": ("FSL matches",),
    },
    {
        "natural_language": "Leaderboard series win pct narrow top 5",
        "action": "leaderboard_win_pct",
        "params": {"min_matches": 15, "limit": 5},
        "expect_substrings": ("75.0%",),
    },
    {
        "natural_language": "Team browse search only",
        "action": "teams_search",
        "params": {"q": "Alpha", "limit": 10},
        "expect_substrings": ("Alpha Squad",),
    },
    {
        "natural_language": "Player browse search limit 12",
        "action": "players_search",
        "params": {"q": "a", "limit": 12},
        "expect_substrings": ("FSL players",),
    },
    {
        "natural_language": "Off-topic should be none",
        "action": "none",
        "params": {},
        "expect_substrings": (),
        "expect_empty": True,
    },
]


@pytest.mark.parametrize(
    "scenario",
    EXEC_MATRIX,
    ids=[f"{i}_{row['action']}" for i, row in enumerate(EXEC_MATRIX)],
)
@pytest.mark.asyncio
async def test_exec_action_supports_scenario(scenario: Dict[str, Any]) -> None:
    assistant = FslAskAssistant(MockLLM(), MockFslDb())
    text, ok = await assistant._exec_action(scenario["action"], scenario["params"])
    assert ok is True
    if scenario.get("expect_empty"):
        assert text == ""
        return
    assert isinstance(text, str) and len(text) > 0
    for frag in scenario.get("expect_substrings") or ():
        assert frag in text, f"missing {frag!r} in:\n{text}"


@pytest.mark.asyncio
async def test_exec_matrix_covers_all_actions() -> None:
    actions = {row["action"] for row in EXEC_MATRIX}
    expected = {
        "none",
        "players_search",
        "player_detail",
        "teams_search",
        "team_detail",
        "team_roster",
        "schedule",
        "team_league_season",
        "solo_division_season",
        "matches",
        "matches_h2h",
        "leaderboard_win_pct",
        "leaderboard_total_wins",
        "leaderboard_maps_won",
        "match_detail",
        "statistics_player",
    }
    missing = expected - actions
    extra = actions - expected
    assert not missing, f"matrix missing actions: {missing}"
    assert not extra, f"matrix unknown actions: {extra}"


UNSUPPORTED_ROUTER_TARGETS = [
    (
        "What build did I use last ranked game?",
        "Mathison replay archive — not FSL league tables.",
    ),
    (
        "Best map win % across divisions for season 8 only using FSL_STATISTICS?",
        "FSL_STATISTICS has no season in our API.",
    ),
    (
        "Tell me a joke about siege tanks.",
        "Not FSL lookup data.",
    ),
]


@pytest.mark.parametrize("question,reason", UNSUPPORTED_ROUTER_TARGETS)
def test_documented_off_topic_examples(question: str, reason: str) -> None:
    """Living documentation for humans + future router golden tests."""
    assert len(question) > 5 and reason


@pytest.mark.parametrize(
    "question,expect_a,expect_b",
    [
        (
            "when was the last game between SirMalagant and CrankyToaster?",
            "SirMalagant",
            "CrankyToaster",
        ),
        ("Last series between FooBar and Baz Qux!", "FooBar", "Baz Qux"),
    ],
)
def test_solo_h2h_pattern_override(question: str, expect_a: str, expect_b: str) -> None:
    plan = _solo_h2h_plan_from_question(question)
    assert plan is not None
    assert plan["action"] == "matches"
    assert plan["params"]["player_name"] == expect_a
    assert plan["params"]["opponent_name"] == expect_b
    assert plan["params"]["season"] is None


def test_solo_h2h_pattern_not_team_schedule_topic() -> None:
    """Team-only phrasing without 'game/match between' should not match the strict patterns."""
    assert _solo_h2h_plan_from_question("which team won season 10") is None


def test_h2h_aggregate_record_between_matches_h2h() -> None:
    p = _solo_h2h_aggregate_plan_from_question(
        "what is the record between NukLeo and DarkMenace ?"
    )
    assert p is not None
    assert p["action"] == "matches_h2h"
    assert p["params"]["player_name"] == "NukLeo"
    assert p["params"]["opponent_name"] == "DarkMenace"
    assert _solo_h2h_plan_from_question(
        "what is the record between NukLeo and DarkMenace ?"
    ) is None


def test_h2h_aggregate_between_players_keyword() -> None:
    """Viewers often say 'between players X and Y' — must not capture 'players' as the name."""
    p = _solo_h2h_aggregate_plan_from_question(
        "what is the record between players NukLeo and DarkMenace ?"
    )
    assert p is not None
    assert p["action"] == "matches_h2h"
    assert p["params"]["player_name"] == "NukLeo"
    assert p["params"]["opponent_name"] == "DarkMenace"


def test_h2h_aggregate_short_duel_ping_name_vs_name() -> None:
    """Twitch-style 'Name vs Name ?' without 'record' — route to matches_h2h like record queries."""
    p = _solo_h2h_aggregate_plan_from_question("NukLeo vs DarkMenace ?")
    assert p is not None
    assert p["action"] == "matches_h2h"
    assert p["params"]["player_name"] == "NukLeo"
    assert p["params"]["opponent_name"] == "DarkMenace"


def test_h2h_aggregate_record_vs_form() -> None:
    p = _solo_h2h_aggregate_plan_from_question(
        "what is the record littlereaper vs cyan ?"
    )
    assert p is not None
    assert p["action"] == "matches_h2h"
    assert p["params"]["player_name"].lower() == "littlereaper"
    assert p["params"]["opponent_name"].lower() == "cyan"


def test_team_roster_players_for_team_name() -> None:
    p = _team_roster_plan_from_question("who are the players for Special Tactics?")
    assert p is not None
    assert p["action"] == "team_roster"
    assert p["params"]["name"] == "Special Tactics"


def test_team_roster_strips_optional_team_prefix() -> None:
    p = _team_roster_plan_from_question("players for team Special Tactics")
    assert p is not None
    assert "Special Tactics" in (p["params"]["name"] or "")
