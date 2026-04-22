"""
DB lookup helpers for ladder Random opponents.

Replays store the actual played race (Terran/Zerg/Protoss), never \"Random\".
We gather intel per concrete race so viewers still see tendencies before spawn.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import utils.tokensArray as tokensArray
from settings import config

logger = logging.getLogger(__name__)

CONCRETE_SC2_RACES: Tuple[str, ...] = ("Terran", "Zerg", "Protoss")


def _date_played_sort_key(row: Dict[str, Any]) -> datetime:
    d = row.get("Date_Played")
    if isinstance(d, datetime):
        return d.replace(tzinfo=None) if d.tzinfo else d
    if isinstance(d, str) and d:
        try:
            return datetime.strptime(d, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    return datetime.min


def _other_player_sc2_id_from_row(row: Dict[str, Any]) -> Optional[str]:
    p1 = str(row.get("Player1_Name", ""))
    p2 = str(row.get("Player2_Name", ""))
    for sn in config.SC2_PLAYER_ACCOUNTS:
        sl = sn.lower()
        if p1.lower() == sl:
            return p2
        if p2.lower() == sl:
            return p1
    return None


def gather_concrete_race_intel_for_random_opponent(
    db,
    opponent_display_name: str,
    streamer_current_race: str,
    log=None,
) -> Tuple[
    Tuple[Tuple[str, Dict[str, Any], List[Any], Optional[List[str]]], ...],
    str,
    Optional[Dict[str, Any]],
    List[Any],
    Optional[List[str]],
]:
    """
    Query Terran / Zerg / Protoss separately for an opponent who is Random on ladder.

    Returns:
        random_race_intel: (race, replay_row, comments, build_steps) per race found
        canonical_opponent_name: SC2_UserId used for successful queries
        primary_db_result: newest replay row by Date_Played (for \"last meeting\" prompt), or None
        merged_comments: saved comments across races, deduped by ReplayId, newest first
        first_build_steps: build steps for the primary row's race, else first non-empty build in T/Z/P order
    """
    log = log or logger
    original = opponent_display_name.strip()
    alias = tokensArray.find_master_name(original)
    canonical = alias if alias is not None else original

    intel: List[Tuple[str, Dict[str, Any], List[Any], Optional[List[str]]]] = []

    for race in CONCRETE_SC2_RACES:
        row = db.check_player_and_race_exists(canonical, race)
        if row is None and canonical.lower() != original.lower():
            row = db.check_player_and_race_exists(original, race)
        if row is None:
            continue

        comments = db.get_player_comments(canonical, race) or []
        if not comments:
            oid = _other_player_sc2_id_from_row(row)
            if oid and oid.strip().lower() != canonical.strip().lower():
                comments = db.get_player_comments(oid, race) or []

        build_steps = db.extract_opponent_build_order(
            canonical, race, streamer_current_race
        )

        intel.append((race, row, comments, build_steps))
        log.debug(
            "[random_intel] opponent=%r race=%s replay_id=%s comments=%d build_len=%s",
            canonical,
            race,
            row.get("ReplayId"),
            len(comments),
            len(build_steps or []) if build_steps else 0,
        )

    if not intel:
        return (), canonical, None, [], None

    _, primary_row, _, primary_build = max(
        intel, key=lambda t: _date_played_sort_key(t[1])
    )

    merged_flat: List[Any] = []
    seen_rid = set()
    for _, _, comments, _ in intel:
        for c in comments:
            rid = c.get("ReplayId") or c.get("replay_id")
            key = (rid, c.get("date_played"))
            if key in seen_rid:
                continue
            seen_rid.add(key)
            merged_flat.append(c)

    merged_flat.sort(key=lambda x: str(x.get("date_played", "")), reverse=True)

    if not primary_build:
        for _, _, _, steps in intel:
            if steps:
                primary_build = steps
                break

    return (
        tuple(intel),
        canonical,
        primary_row,
        merged_flat,
        primary_build,
    )
