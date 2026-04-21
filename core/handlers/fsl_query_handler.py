"""
Twitch command: FSL facts from api-server /api/v1/fsl/* (psistorm).

Requires DB_MODE=api and api-server with psistorm_db_config. Not an open-ended NL bot.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import settings.config as config
import utils.tokensArray as tokensArray
from core.command_service import CommandContext, ICommandHandler
from core.repositories.sql_player_repository import SqlPlayerRepository

logger = logging.getLogger(__name__)


def _name_in_display(name: str, cell: Optional[str]) -> bool:
    n, v = name.lower().strip(), (cell or "").lower().strip()
    if not n or not v:
        return False
    return n in v or v in n


def player_series_wins_losses(rows: List[Dict[str, Any]], raw_name: str) -> Tuple[int, int]:
    w = l = 0
    for r in rows:
        if _name_in_display(raw_name, r.get("winner_name")):
            w += 1
        elif _name_in_display(raw_name, r.get("loser_name")):
            l += 1
    return w, l


def player_series_record_line(rows: List[Dict[str, Any]], raw_name: str, season: Optional[int]) -> str:
    w, l = player_series_wins_losses(rows, raw_name)
    tot = w + l
    if tot == 0:
        return ""
    pct = 100.0 * w / tot
    scope = f"season {season}" if season is not None else "this sample"
    return f"{raw_name} — match record ({scope}): {w}-{l} ({tot} series, {pct:.1f}% wins)."


def _norm_name(s: str) -> str:
    return " ".join((s or "").lower().split())


def _h2h_name_match_score(query: str, display_name: str) -> int:
    """
    Score how well `query` (viewer phrase) refers to `display_name` (DB Real_Name).
    Higher = stronger. Avoids bug where both queries substring-match the same winner
    (e.g. 'little' vs 'littlereaper' vs winner LittleReaper) and only the first `if` branch counted.
    """
    q = _norm_name(query)
    d = _norm_name(display_name)
    if not q or not d:
        return 0
    if q == d:
        return 2000 + len(q)
    if len(q) >= 3 and q in d:
        return 1000 + len(q)
    if len(d) >= 3 and d in q:
        return 800 + len(d)
    return 0


def _h2h_winner_side(raw_a: str, raw_b: str, winner_name: Optional[str]) -> Optional[int]:
    """0 = raw_a won series, 1 = raw_b won, None if unclear."""
    if not winner_name:
        return None
    sa = _h2h_name_match_score(raw_a, winner_name)
    sb = _h2h_name_match_score(raw_b, winner_name)

    def _prefer_longer_query() -> int:
        la, lb = len(_norm_name(raw_a)), len(_norm_name(raw_b))
        return 0 if la >= lb else 1

    if sa == 0 and sb == 0:
        ma = _name_in_display(raw_a, winner_name)
        mb = _name_in_display(raw_b, winner_name)
        if ma and not mb:
            return 0
        if mb and not ma:
            return 1
        if ma and mb:
            return _prefer_longer_query()
        return None

    if sa > sb:
        return 0
    if sb > sa:
        return 1
    return _prefer_longer_query()


def _h2h_series_summary(rows: List[Dict[str, Any]], raw_a: str, raw_b: str) -> str:
    if not rows:
        return ""
    wa = wb = 0
    unmatched = 0
    for r in rows:
        win = r.get("winner_name")
        side = _h2h_winner_side(raw_a, raw_b, win if isinstance(win, str) else None)
        if side == 0:
            wa += 1
        elif side == 1:
            wb += 1
        else:
            unmatched += 1
    n = len(rows)
    head = f"Head-to-head (FSL series in this list, n={n}): {raw_a} {wa} - {wb} {raw_b}."
    if unmatched:
        head += f" ({unmatched} row(s) could not attribute winner to either name — check spelling.)"
    return head


def _usage() -> str:
    return (
        "FSL (league DB): "
        "fsl help | "
        "fsl players <query> | "
        "fsl player <name> | "
        "fsl team <query> | "
        "fsl schedule [season [week]] | "
        "fsl matches <player> [season <n>]"
    )


class FslQueryHandler(ICommandHandler):
    """Command prefix: `fsl` (subcommands: help, players, player, team, schedule, matches)."""

    def __init__(self, player_repo: SqlPlayerRepository):
        self.player_repo = player_repo

    def _db(self) -> Any:
        return self.player_repo.db

    def _fsl_enabled(self) -> bool:
        if not getattr(config, "ENABLE_FSL_DB_COMMANDS", True):
            return False
        db = self._db()
        return hasattr(db, "fsl_players_search") and callable(getattr(db, "fsl_players_search"))

    async def _run(self, fn, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))

    async def handle(self, context: CommandContext, args: str) -> None:
        if not self._fsl_enabled():
            await context.chat_service.send_message(
                context.channel,
                "FSL commands are off or unavailable. Use DB_MODE=api, deploy api-server FSL routes, "
                "and set ENABLE_FSL_DB_COMMANDS True in config.",
            )
            return

        parts = args.strip().split()
        if not parts:
            out = _usage()
            await context.chat_service.send_message(
                context.channel,
                tokensArray.truncate_to_byte_limit(out, config.TWITCH_CHAT_BYTE_LIMIT),
            )
            return

        sub = parts[0].lower()
        try:
            if sub in ("help", "?"):
                out = _usage()
            elif sub in ("players", "playersearch"):
                out = await self._cmd_players_search(parts)
            elif sub == "player":
                out = await self._cmd_player_detail(parts)
            elif sub in ("team", "teams"):
                out = await self._cmd_team_search(parts)
            elif sub == "schedule":
                out = await self._cmd_schedule(parts)
            elif sub in ("matches", "match"):
                out = await self._cmd_matches(parts)
            else:
                out = f"Unknown fsl subcommand '{sub}'. {_usage()}"
        except Exception as e:
            logger.exception("FSL command error: %s", e)
            err = str(e)
            if "503" in err or "FSL unavailable" in err:
                err = "FSL API unavailable (check api-server psistorm config)."
            out = f"FSL error: {err[:200]}"

        await context.chat_service.send_message(
            context.channel,
            tokensArray.truncate_to_byte_limit(out, config.TWITCH_CHAT_BYTE_LIMIT),
        )

    async def _cmd_players_search(self, parts: List[str]) -> str:
        q = " ".join(parts[1:]).strip()
        if not q:
            return "Usage: fsl players <search text>"
        data = await self._run(self._db().fsl_players_search, q, 12)
        rows: List[Dict[str, Any]] = data.get("players") or []
        if not rows:
            return f"No FSL players matching {q!r}."
        bits = []
        for r in rows[:10]:
            tid = r.get("Team_Name") or ""
            bits.append(f"{r.get('Real_Name')} (id {r.get('Player_ID')})" + (f" [{tid}]" if tid else ""))
        return "FSL: " + " | ".join(bits)

    async def _cmd_player_detail(self, parts: List[str]) -> str:
        name = " ".join(parts[1:]).strip()
        if not name:
            return "Usage: fsl player <exact or best-match name>"
        db = self._db()
        row = await self._run(db.fsl_player_by_name_exact, name)
        if not row:
            data = await self._run(db.fsl_players_search, name, 5)
            rows = data.get("players") or []
            if not rows:
                return f"No FSL player named {name!r}."
            row = rows[0]
            name = row.get("Real_Name", name)
        pid = int(row["Player_ID"])
        stats = await self._run(db.fsl_statistics_for_player, pid)
        stat_rows = stats.get("statistics") or []
        team = row.get("Team_Name") or ""
        head = f"{row.get('Real_Name')} (id {pid})" + (f" team {team}" if team else "")
        if not stat_rows:
            return head + " — no FSL_STATISTICS rows."
        lines = [head + " — FSL stats (div/race maps sets):"]
        for s in stat_rows[:8]:
            lines.append(
                f"  {s.get('Division')}/{s.get('Race')}: "
                f"maps {s.get('MapsW', 0)}-{s.get('MapsL', 0)} "
                f"sets {s.get('SetsW', 0)}-{s.get('SetsL', 0)}"
            )
        return "\n".join(lines)

    async def _cmd_team_search(self, parts: List[str]) -> str:
        q = " ".join(parts[1:]).strip()
        if not q:
            return "Usage: fsl team <search text>"
        data = await self._run(self._db().fsl_teams_search, q, 12)
        rows = data.get("teams") or []
        if not rows:
            return f"No FSL teams matching {q!r}."
        bits = [f"{r.get('Team_Name')} (id {r.get('Team_ID')}, {r.get('Status')})" for r in rows[:10]]
        return "FSL teams: " + " | ".join(bits)

    async def _cmd_schedule(self, parts: List[str]) -> str:
        season: Optional[int] = None
        week: Optional[int] = None
        if len(parts) >= 2 and parts[1].isdigit():
            season = int(parts[1])
        if len(parts) >= 3 and parts[2].isdigit():
            week = int(parts[2])
        data = await self._run(self._db().fsl_schedule, season, week, 15)
        rows = data.get("schedule") or []
        if not rows:
            return "No schedule rows for that filter."
        lines = []
        for s in rows[:12]:
            md = s.get("match_date") or ""
            lines.append(
                f"S{s.get('season')} W{s.get('week_number')}: "
                f"{s.get('team1_name')} vs {s.get('team2_name')} "
                f"{s.get('team1_score')}-{s.get('team2_score')} ({md}) {s.get('status', '')}"
            )
        return "FSL schedule:\n" + "\n".join(lines)

    async def _cmd_matches(self, parts: List[str]) -> str:
        tail = " ".join(parts[1:]).strip()
        if not tail:
            return "Usage: fsl matches <player> | <p1> vs <p2> [season <n>]"

        db = self._db()
        loop = asyncio.get_running_loop()

        # Head-to-head: "NameA vs NameB" optional "season N"
        m_h2h = re.match(
            r"^(?P<p1>.+?)\s+vs\s+(?P<p2>.+?)(?:\s+season\s+(?P<s>\d+))?\s*$",
            tail,
            re.IGNORECASE | re.DOTALL,
        )
        if m_h2h:
            p1 = m_h2h.group("p1").strip()
            p2 = m_h2h.group("p2").strip()
            season = int(m_h2h.group("s")) if m_h2h.group("s") else None
            data = await loop.run_in_executor(
                None,
                lambda: db.fsl_matches(
                    season=season,
                    player_name=p1,
                    player_id=None,
                    opponent_name=p2,
                    limit=120,
                ),
            )
            rows = data.get("matches") or []
            if not rows:
                return (
                    f"No FSL matches between {p1!r} and {p2!r}"
                    + (f" (season {season})" if season is not None else "")
                    + "."
                )
            lines = [_h2h_series_summary(rows, p1, p2)]
            for r in rows[:12]:
                lines.append(
                    f"{r.get('winner_name')} > {r.get('loser_name')} "
                    f"{r.get('map_win')}-{r.get('map_loss')} (s{r.get('season')}, id {r.get('fsl_match_id')})"
                )
            return "FSL matches:\n" + "\n".join(lines)

        m = re.search(
            r"^(.+?)\s+season\s+(\d+)\s*$",
            tail,
            re.IGNORECASE,
        )
        season: Optional[int] = None
        player_q: str
        if m:
            player_q = m.group(1).strip()
            season = int(m.group(2))
        else:
            player_q = tail

        match_limit = 120 if season is not None else 14
        data = await loop.run_in_executor(
            None,
            lambda: db.fsl_matches(
                season=season,
                player_name=player_q,
                player_id=None,
                opponent_name=None,
                limit=match_limit,
            ),
        )
        rows = data.get("matches") or []
        if not rows:
            return f"No FSL matches for player {player_q!r}" + (f" season {season}" if season is not None else "") + "."
        lines = []
        if season is not None:
            sr = player_series_record_line(rows, player_q, season)
            if sr:
                lines.append(sr)
        for r in rows[:10]:
            lines.append(
                f"{r.get('winner_name')} > {r.get('loser_name')} "
                f"{r.get('map_win')}-{r.get('map_loss')} (s{r.get('season')}, id {r.get('fsl_match_id')})"
            )
        return "FSL matches:\n" + "\n".join(lines)
