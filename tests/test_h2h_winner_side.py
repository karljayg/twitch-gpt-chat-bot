"""Head-to-head series count: winner must be attributed to the best-matching query, not `if/elif` order."""
from __future__ import annotations

from typing import Any, Dict, List

import pytest

from core.handlers.fsl_query_handler import _h2h_series_summary


def _row(winner: str, loser: str, mid: int = 1, season: int = 9) -> Dict[str, Any]:
    return {
        "winner_name": winner,
        "loser_name": loser,
        "fsl_match_id": mid,
        "season": season,
        "map_win": 2,
        "map_loss": 0,
    }


def test_h2h_prefers_longer_query_when_both_substring_match_winner() -> None:
    """little vs littlereaper vs winner LittleReaper — must count for littlereaper, not first branch."""
    rows: List[Dict[str, Any]] = [_row("LittleReaper", "cyan", mid=409)]
    out = _h2h_series_summary(rows, raw_a="little", raw_b="littlereaper")
    assert "0 - 1 littlereaper" in out or out.endswith(
        "littlereaper."
    ), out


def test_h2h_littlereaper_vs_cyan_counts_four_series() -> None:
    rows = [
        _row("cyan", "LittleReaper", mid=465, season=8),
        _row("LittleReaper", "cyan", mid=409, season=7),
        _row("LittleReaper", "cyan", mid=319, season=6),
        _row("LittleReaper", "cyan", mid=236, season=5),
    ]
    out = _h2h_series_summary(rows, raw_a="Cyan", raw_b="littlereaper")
    assert "Cyan 1 - 3 littlereaper" in out
    assert "n=4" in out


def test_h2h_darkmenace_sweep() -> None:
    rows = [
        _row("DarkMenace", "HarOuz", mid=609, season=9),
        _row("DarkMenace", "HarOuz", mid=480, season=8),
        _row("DarkMenace", "HarOuz", mid=457, season=7),
        _row("DarkMenace", "HarOuz", mid=447, season=7),
    ]
    out = _h2h_series_summary(rows, raw_a="Darkmenace", raw_b="Harouz")
    assert "Darkmenace 4 - 0 Harouz" in out
    assert "n=4" in out


@pytest.mark.parametrize(
    "raw_a, raw_b,winner,expect_side",
    [
        ("LittleReaper", "Cyan", "cyan", 1),
        ("Cyan", "LittleReaper", "cyan", 0),
        ("LittleReaper", "cyan", "LittleReaper", 0),
    ],
)
def test_winner_side_basic(raw_a: str, raw_b: str, winner: str, expect_side: int) -> None:
    from core.handlers.fsl_query_handler import _h2h_winner_side

    side = _h2h_winner_side(raw_a, raw_b, winner)
    assert side == expect_side
