"""
One-line matchup facts for pre-game → replay-summary GenAI (not Twitch chat).

When both names resolve in FSL, prefer career map totals from /fsl/matches/h2h.
Otherwise use replay-archive head-to-head (same DB as get_head_to_head_matchup).
"""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, List, Optional, Sequence, Tuple

log = logging.getLogger(__name__)


def _fsl_commands_enabled() -> bool:
    from settings import config

    return bool(getattr(config, "ENABLE_FSL_DB_COMMANDS", True))


def _player_row_real_name(row: Optional[dict]) -> Optional[str]:
    if not row:
        return None
    for k in ("Real_Name", "real_name"):
        v = row.get(k)
        if v and str(v).strip():
            return str(v).strip()
    return None


def resolve_fsl_real_name(db: Any, *name_hints: str) -> Optional[str]:
    """Best-effort FSL `Players.Real_Name` for SC2 / chat spellings."""
    if not _fsl_commands_enabled() or not hasattr(db, "fsl_player_by_name_exact"):
        return None
    ordered = _dedupe_name_hints(name_hints)
    if not ordered:
        return None
    for hint in ordered:
        try:
            row = db.fsl_player_by_name_exact(hint)
        except Exception as e:
            log.debug("FSL fsl_player_by_name_exact failed for %r: %s", hint, e)
            continue
        rn = _player_row_real_name(row)
        if rn:
            return rn
    q0 = ordered[0] if ordered else ""
    if not q0 or not hasattr(db, "fsl_players_search"):
        return None
    try:
        data = db.fsl_players_search(q0, 12) or {}
    except Exception as e:
        log.debug("FSL fsl_players_search failed for %r: %s", q0, e)
        return None
    players = data.get("players") or []
    qlow = q0.lower()
    for p in players:
        rn = _player_row_real_name(p)
        if rn and rn.lower() == qlow:
            return rn
    for p in players:
        rn = _player_row_real_name(p)
        if not rn:
            continue
        rlow = rn.lower()
        if len(qlow) >= 3 and (qlow in rlow or rlow in qlow):
            return rn
    return None


def _streamer_name_hints() -> Tuple[str, ...]:
    from settings import config

    out: List[str] = []
    nick = getattr(config, "STREAMER_NICKNAME", None)
    if nick and str(nick).strip():
        out.append(str(nick).strip())
    for a in getattr(config, "SC2_PLAYER_ACCOUNTS", None) or []:
        s = str(a).strip()
        if s and s.lower() not in {x.lower() for x in out}:
            out.append(s)
    for a in getattr(config, "SC2_BARCODE_ACCOUNTS", None) or []:
        s = str(a).strip()
        if s and s.lower() not in {x.lower() for x in out}:
            out.append(s)
    return tuple(_dedupe_name_hints(out))


def _ascii_fold(s: str) -> str:
    """Strip combining marks (e.g. ö → o) so replay DB ASCII names still match."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def _dedupe_name_hints(seq: Sequence[str]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for x in seq:
        s = str(x).strip() if x else ""
        if not s:
            continue
        for variant in (s, _ascii_fold(s)):
            v = variant.strip()
            if not v:
                continue
            k = v.lower()
            if k in seen:
                continue
            seen.add(k)
            out.append(v)
    return out


def replay_archive_head_to_head_totals_multi(
    db: Any,
    player_a_hints: Sequence[str],
    player_b_hints: Sequence[str],
) -> Optional[Tuple[int, int]]:
    """First non-empty head-to-head between any hint pair (wins for first hint vs second)."""
    for a in _dedupe_name_hints(player_a_hints):
        for b in _dedupe_name_hints(player_b_hints):
            tot = replay_archive_head_to_head_totals(db, a, b)
            if tot:
                return tot
    return None


def replay_h2h_streamer_vs_opponent(
    db: Any, opponent_hints: Sequence[str]
) -> Optional[Tuple[int, int]]:
    """(streamer_wins, streamer_losses) from replay DB when record lines did not parse."""
    tot = replay_archive_head_to_head_totals_multi(
        db, list(_streamer_name_hints()), list(opponent_hints)
    )
    if not tot:
        return None
    return tot[0], tot[1]


def replay_archive_head_to_head_totals(
    db: Any, player_a: str, player_b: str
) -> Optional[Tuple[int, int]]:
    """Wins for `player_a` vs `player_b` summed over race matchups (replay DB)."""
    if not hasattr(db, "get_head_to_head_matchup"):
        return None
    try:
        rows = db.get_head_to_head_matchup(player_a, player_b)
    except Exception as e:
        log.debug("get_head_to_head_matchup failed: %s", e)
        return None
    if not rows:
        return None
    wa = wb = 0
    for matchup in rows:
        m = re.search(r"(\d+)\s+wins?\s*-\s*(\d+)\s+wins?", matchup)
        if m:
            wa += int(m.group(1))
            wb += int(m.group(2))
    if wa == 0 and wb == 0:
        return None
    return wa, wb


def fsl_career_maps_sentence(
    db: Any,
    label_a: str,
    label_b: str,
    api_query_a: str,
    api_query_b: str,
) -> Optional[str]:
    """e.g. label_a is 12-9 vs label_b in FSL (career maps)."""
    if not hasattr(db, "fsl_matches_h2h"):
        return None
    try:
        data = db.fsl_matches_h2h(api_query_a, api_query_b) or {}
    except Exception as e:
        log.debug("fsl_matches_h2h failed: %s", e)
        return None
    if data.get("_h2h_endpoint_unavailable"):
        return None
    row = data.get("h2h") if isinstance(data.get("h2h"), dict) else {}
    if not row:
        return None
    st = int(row.get("series_total") or 0)
    ma = int(row.get("maps_won_a") or 0)
    mb = int(row.get("maps_won_b") or 0)
    if st == 0 and ma == 0 and mb == 0:
        return None
    return f"{label_a} is {ma}-{mb} vs {label_b} in FSL (career maps)."


def replay_h2h_sentence(display_a: str, display_b: str, wins_a: int, wins_b: int) -> str:
    return f"{display_a} is {wins_a}-{wins_b} vs {display_b}."


def build_dual_player_tidbit(db: Any, p1: str, p2: str, logger=None) -> Optional[str]:
    """Observer 1v1: FSL map H2H if both in FSL, else replay-archive H2H."""
    _ = logger
    r1 = resolve_fsl_real_name(db, p1)
    r2 = resolve_fsl_real_name(db, p2)
    if r1 and r2:
        s = fsl_career_maps_sentence(db, p1, p2, r1, r2)
        if s:
            return s
    tot = replay_archive_head_to_head_totals(db, p1, p2)
    if not tot:
        return None
    wa, wb = tot
    return replay_h2h_sentence(p1, p2, wa, wb)


def build_streamer_vs_opponent_tidbit(
    db: Any,
    opponent_display: str,
    opponent_name_hints: Sequence[str],
    logger=None,
) -> Optional[str]:
    from settings import config

    _ = logger
    hints_o = _dedupe_name_hints((opponent_display, *opponent_name_hints))

    r_o = resolve_fsl_real_name(db, *hints_o)
    r_s: Optional[str] = None
    for h in _streamer_name_hints():
        r_s = resolve_fsl_real_name(db, h)
        if r_s:
            break
    sn = getattr(config, "STREAMER_NICKNAME", "Streamer")
    if r_s and r_o:
        s = fsl_career_maps_sentence(db, sn, opponent_display, r_s, r_o)
        if s:
            return s
    tot = replay_archive_head_to_head_totals_multi(
        db, list(_streamer_name_hints()), hints_o
    )
    if tot:
        wa, wb = tot
        return replay_h2h_sentence(sn, opponent_display, wa, wb)
    return None


def set_pregame_matchup_blurb(bot: Any, line: Optional[str]) -> None:
    """Stash for replay_summary prepending (consumed in sc2_game_utils)."""
    if line and str(line).strip():
        setattr(bot, "_pregame_matchup_blurb", str(line).strip())


def clear_pregame_matchup_blurb(bot: Any) -> None:
    setattr(bot, "_pregame_matchup_blurb", None)
