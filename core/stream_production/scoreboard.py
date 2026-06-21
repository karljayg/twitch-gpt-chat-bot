"""Parse and diff the production scoreboards so Mathison can attribute a team-score
point to the exact player matchup that changed.

Two sources (both configurable, both optional):
- Team-league CSV (e.g. 2026/scoreboard.csv): team totals + every per-matchup row.
- Custom-game JSON (data/custom_scoreboard.json): the featured matchup(s).

The "which one is in play" question is answered by diffing against the previously
seen parse: whichever scoreboard's row scores changed is the active one.
"""
import csv
import io
import re
from dataclasses import dataclass
from typing import List, Optional

_RACE_PREFIX = re.compile(r"^\(\s*[ZPTRzptr]\s*\)\s*")


def strip_race(name: Optional[str]) -> str:
    if not name:
        return ""
    return _RACE_PREFIX.sub("", str(name)).strip()


def _to_int(v) -> Optional[int]:
    try:
        s = str(v).strip()
        if s == "":
            return None
        return int(float(s))
    except (TypeError, ValueError):
        return None


def _norm(name: str) -> str:
    return strip_race(name).strip().lower()


@dataclass
class Matchup:
    a: str
    score_a: Optional[int]
    b: str
    score_b: Optional[int]
    kind: str = "1v1"

    def format(self) -> str:
        sa = self.score_a if self.score_a is not None else 0
        sb = self.score_b if self.score_b is not None else 0
        return f"{self.a} {sa}-{sb} {self.b}"

    def key(self):
        return tuple(sorted([_norm(self.a), _norm(self.b)]))

    def has_player(self, player: str) -> bool:
        pl = _norm(player)
        if not pl:
            return False
        sides = []
        for side in (self.a, self.b):
            sides.extend(t for t in _norm(side).replace("&", " ").split())
        return pl in sides


def parse_teamleague_csv(text: str) -> dict:
    """Parse the team-league scoreboard CSV.

    Layout (quoted): a team-total row, a 'map 1/map 2' header, then rows whose
    col[1] is '1v1'/'2v2'. Player cols carry a race prefix like '(P)Neutrophil'.
    """
    result = {"team_a": None, "score_a": None, "team_b": None, "score_b": None, "matchups": []}
    if not text:
        return result
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except Exception:
        return result

    for r in rows:
        if len(r) < 9:
            continue
        kind = (r[1] or "").strip().lower()
        if kind in ("1v1", "2v2"):
            a, a2 = strip_race(r[2]), strip_race(r[3])
            b, b2 = strip_race(r[6]), strip_race(r[7])
            if not a or not b:
                continue
            name_a = a if not a2 else f"{a} & {a2}"
            name_b = b if not b2 else f"{b} & {b2}"
            result["matchups"].append(
                Matchup(name_a, _to_int(r[4]), name_b, _to_int(r[8]), kind)
            )
        elif result["team_a"] is None:
            t_a, t_b = strip_race(r[2]), strip_race(r[6])
            sa, sb = _to_int(r[4]), _to_int(r[8])
            # The team-total row has both names + both scores and is not a map header.
            if t_a and t_b and sa is not None and sb is not None:
                result["team_a"], result["score_a"] = t_a, sa
                result["team_b"], result["score_b"] = t_b, sb
    return result


def parse_custom_scoreboard(obj: Optional[dict]) -> dict:
    result = {"matchups": []}
    if not obj:
        return result
    for m in obj.get("matches") or []:
        a, b = strip_race(m.get("a")), strip_race(m.get("b"))
        if not a or not b:
            continue
        result["matchups"].append(
            Matchup(a, _to_int(m.get("scoreA")), b, _to_int(m.get("scoreB")))
        )
    return result


def diff_matchups(prev: List[Matchup], curr: List[Matchup]) -> List[Matchup]:
    """Return current matchups whose score changed versus the previous parse."""
    pmap = {m.key(): m for m in (prev or [])}
    changed = []
    for m in curr or []:
        p = pmap.get(m.key())
        if p is None:
            continue
        if (m.score_a, m.score_b) != (p.score_a, p.score_b):
            changed.append(m)
    return changed


def find_matchup_for_player(matchups: List[Matchup], player: str) -> Optional[Matchup]:
    for m in matchups or []:
        if m.has_player(player):
            return m
    return None


def changed_with_winner(prev: List[Matchup], curr: List[Matchup]) -> List[dict]:
    """Like diff_matchups, but also reports WHICH side just scored (the game winner),
    by checking which player's score increased. This is what lets us attribute the
    point correctly instead of letting the LLM guess."""
    pmap = {m.key(): m for m in (prev or [])}
    out = []
    for m in curr or []:
        p = pmap.get(m.key())
        if p is None:
            continue
        if (m.score_a, m.score_b) == (p.score_a, p.score_b):
            continue
        da = (m.score_a or 0) - (p.score_a or 0)
        db = (m.score_b or 0) - (p.score_b or 0)
        winner = winner_score = loser = loser_score = None
        if da > 0 and db <= 0:
            winner, winner_score, loser, loser_score = m.a, m.score_a, m.b, m.score_b
        elif db > 0 and da <= 0:
            winner, winner_score, loser, loser_score = m.b, m.score_b, m.a, m.score_a
        out.append({
            "matchup": m,
            "winner": winner,
            "winner_score": winner_score,
            "loser": loser,
            "loser_score": loser_score,
        })
    return out


def _leader_suffix(a: str, sa: Optional[int], b: str, sb: Optional[int]) -> str:
    sa = sa or 0
    sb = sb or 0
    if sa > sb:
        return f" ({a} leads {sa}-{sb})"
    if sb > sa:
        return f" ({b} leads {sb}-{sa})"
    return f" (tied {sa}-{sb})"


def describe_matchup_record(
    m: Matchup,
    winner: Optional[str] = None,
    winner_score: Optional[int] = None,
    loser: Optional[str] = None,
    loser_score: Optional[int] = None,
) -> str:
    """Unambiguous, flip-proof head-to-head text: every number is bound to its player
    by name, plus an explicit 'who leads' so the model cannot reverse the score."""
    if winner and loser:
        return (
            f"latest game won by {winner}; head-to-head is now "
            f"{winner}: {winner_score}, {loser}: {loser_score}"
            + _leader_suffix(winner, winner_score, loser, loser_score)
        )
    return (
        f"head-to-head is now {m.a}: {m.score_a}, {m.b}: {m.score_b}"
        + _leader_suffix(m.a, m.score_a, m.b, m.score_b)
    )
