"""Deterministic Code S champion reply from FACTS (no format LLM)."""

from core.fsl_natural_language import (
    _draft_solo_division_champion_reply,
    _parse_solo_division_first_place,
    _question_mentions_solo_code_letter,
    _solo_division_season_plan_from_question,
)

SAMPLE_FACTS = """Season 2 solo league Code S (series W-L from fsl_matches rows with this season and t_code; 14 match rows).
Official champion for this division/season (Players.Championship_Record): sef [player_id 99]. Raw field: Code S season 2 champion
Standings rank (1 = best by wins desc, losses asc): 1) sef 8-2 ; 2) Other 7-3
First place / division leader(s), rank 1 — viewer phrases **champion**, **won**, **who won**, **first place** mean THIS line (not missing data): sef (8-2).
Second place player(s) (rank 2): Other.
"""

# Mimics API with no Championship_Record match — rank 1 in standings must NOT become "champion" in reply.
FACTS_STANDINGS_ONLY_NO_OFFICIAL = """Season 3 solo league Code S (series W-L from fsl_matches rows with this season and t_code; 14 match rows).
**Official solo champion** comes from **`Players.Championship_Record`** only. This API call did **not** match stored text for that title — standings below are **schedule/series record**, not definitive champion title.
Standings rank (series W-L; identical W-L breaks by map_margin sum, then H2H among tied): 1) Neutrophil 6-1 map_margin=5 ; 2) VeryCool 5-2 map_margin=3
Standings leader by series W-L (fsl_matches), rank 1 — **not** synonymous with **`Players.Championship_Record`** champion title: Neutrophil (6-1).
"""


def test_parse_first_place():
    p = _parse_solo_division_first_place(SAMPLE_FACTS)
    assert p is not None
    names, wl, tied = p
    assert names == ("sef",)
    assert wl == (8, 2)
    assert tied is False


def test_official_champion_in_deterministic_reply():
    a = _draft_solo_division_champion_reply(
        SAMPLE_FACTS, "who was the champ in code s in season 2 ?"
    )
    assert a
    assert "Players.Championship_Record" in a
    assert "sef" in a


def test_champion_questions_same_reply():
    q1 = "who was champion for code s in season 2 ?"
    q2 = "which player was code s champion for season 2 ?"
    q_champ = "who was the champ for code s in season 2 ?"
    q_the = "who was the champion for code s in season 2 ?"
    ref = _draft_solo_division_champion_reply(SAMPLE_FACTS, q2)
    assert ref
    for q in (q1, q_champ, q_the):
        assert _draft_solo_division_champion_reply(SAMPLE_FACTS, q) == ref
    assert "sef" in ref
    assert "Code S" in ref
    assert "season 2" in ref.lower()


def test_second_place_question_skips_deterministic():
    q = "who got 2nd in code S in season 2"
    assert _draft_solo_division_champion_reply(SAMPLE_FACTS, q) is None


def test_champion_question_never_invents_name_from_standings():
    a = _draft_solo_division_champion_reply(
        FACTS_STANDINGS_ONLY_NO_OFFICIAL,
        "who was the champ of season 3 code s ?",
    )
    assert a
    assert "Neutrophil" not in a
    assert "series W/L only" in a or "No matching row" in a


def test_code_s_division_case_insensitive():
    assert _question_mentions_solo_code_letter("who won Code S season 2")
    assert _question_mentions_solo_code_letter("who won code s season 2")
    assert _question_mentions_solo_code_letter("CODE A games")
    ref = _draft_solo_division_champion_reply(
        SAMPLE_FACTS, "who was the champion for Code S in season 2 ?"
    )
    assert ref and "sef" in ref


def test_who_won_triggers_same_deterministic_champion_reply():
    """Colloquial 'who won' must match champion intent (same as 'champion')."""
    q = "who won season 2 code s ?"
    ref = _draft_solo_division_champion_reply(SAMPLE_FACTS, q)
    assert ref and "sef" in ref


def test_router_override_who_won_code_a_season():
    """Avoid LLM routing 'who won season N code A' to team league."""
    plan = _solo_division_season_plan_from_question("who won season 1 code A ?")
    assert plan == {
        "action": "solo_division_season",
        "params": {"season": 1, "division": "A"},
        "reason": "solo division code + season pattern",
    }


def test_router_override_no_steal_without_intent_keyword():
    plan = _solo_division_season_plan_from_question("season 1 code A DarkMenace vs HarOuz")
    assert plan is None
