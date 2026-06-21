"""Async monitor for the Stream Production Status API.

Mirrors SC2Adapter's shape: a poll loop that wraps the blocking HTTP client in an
executor. New events are coalesced (anti-spam); when a burst settles, one summary
is logged and (optionally) spoken in Twitch chat.

First slice is safe-by-default: with STREAM_PRODUCTION_ANNOUNCE_ENABLED=False the
adapter only logs what it *would* say, so you can watch real production traffic and
tune the windows before letting Mathison talk.
"""
import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Optional

import settings.config as config
from core.stream_production.client import StreamProductionClient
from core.stream_production.coalescer import (
    EventCoalescer,
    FlushBatch,
    build_summary_prompt,
    extract_llm_text,
    compose_statement,
)
from core.stream_production.scoreboard import (
    parse_teamleague_csv,
    parse_custom_scoreboard,
    changed_with_winner,
    find_matchup_for_player,
    describe_matchup_record,
)

logger = logging.getLogger(__name__)

MAX_LOG_SIZE = 200 * 1024  # 200KB


class StreamProductionAdapter:
    def __init__(self, bot_core=None, client=None, coalescer=None):
        self.bot_core = bot_core
        self.client = client or StreamProductionClient()
        self.coalescer = coalescer or EventCoalescer()
        self.running = False
        self.last_seq = 0
        self.poll_seconds = getattr(config, "STREAM_PRODUCTION_POLL_SECONDS", 2)
        self.activity_log = getattr(
            config, "STREAM_PRODUCTION_ACTIVITY_LOG", "stream_production_activity_log.txt"
        )
        self._was_alive: Optional[bool] = None
        # path -> last parsed list[Matchup], for change detection ("which scoreboard changed")
        self._prev_scoreboards: dict = {}

    async def start_monitoring(self):
        self.running = True
        logger.info("Stream Production monitoring started")
        loop = asyncio.get_event_loop()

        # Baseline poll: adopt current seq and mark existing events as seen so a
        # restart mid-match doesn't replay old events into chat.
        try:
            baseline = await loop.run_in_executor(None, self.client.fetch_status, 0)
            if baseline is not None:
                if baseline.seq:
                    self.last_seq = baseline.seq
                self.coalescer.prime_seen(baseline.recent_events)
                self._was_alive = self._is_alive(baseline)
                logger.info(
                    f"Stream Production baseline: seq={baseline.seq} "
                    f"alive={self._was_alive} ({len(baseline.recent_events)} existing events ignored)"
                )
                # Baseline the scoreboards so the first post-point diff detects the change.
                for label, rel_path, kind in self._scoreboard_sources():
                    try:
                        self._prev_scoreboards[rel_path] = await loop.run_in_executor(
                            None, self._fetch_parse_scoreboard, rel_path, kind
                        )
                    except Exception as e:
                        logger.debug(f"scoreboard baseline failed ({rel_path}): {e}")
        except Exception as e:
            logger.debug(f"Stream production baseline poll failed: {e}")

        while self.running:
            try:
                snapshot = await loop.run_in_executor(None, self.client.fetch_status, self.last_seq)
                now = time.monotonic()

                if snapshot is not None:
                    if snapshot.seq:
                        self.last_seq = snapshot.seq

                    alive = self._is_alive(snapshot)
                    self._note_liveness(alive)

                    if alive and snapshot.recent_events:
                        self._log_raw_events(snapshot)
                        self.coalescer.add(snapshot.recent_events, snapshot, now)

                # Always poll for a flush (so a burst that ended right before the
                # stream went stale still gets spoken).
                batch = self.coalescer.poll(now)
                if batch is not None:
                    await self._handle_batch(batch)

            except Exception as e:
                logger.debug(f"Stream production poll error: {e}")

            await asyncio.sleep(self.poll_seconds)

    def stop(self):
        self.running = False

    # --- liveness ---------------------------------------------------------

    def _is_alive(self, snapshot) -> bool:
        if not snapshot.stream_alive:
            return False
        max_age = getattr(config, "STREAM_PRODUCTION_MAX_HEARTBEAT_AGE_MS", 30000)
        age = snapshot.heartbeat_age_ms
        if age is not None and max_age and age > max_age:
            return False
        return True

    def _note_liveness(self, alive: bool):
        if alive != self._was_alive:
            logger.info(f"Stream production feed {'ALIVE' if alive else 'stale/offline'}")
            self._was_alive = alive

    # --- batch handling ---------------------------------------------------

    async def _handle_batch(self, batch: FlushBatch):
        self._log_batch(batch)

        if not batch.significant:
            return

        if not getattr(config, "STREAM_PRODUCTION_ANNOUNCE_ENABLED", False):
            logger.info(f"[stream-production] (announce OFF) would say from: {batch.lines}")
            return

        message = await self._build_message(batch)
        if message:
            await self._emit_chat(message)

    async def _build_message(self, batch: FlushBatch) -> Optional[str]:
        sb_info = await self._resolve_scoreboard_info(batch)

        # Default: fully deterministic statement (no LLM judgment calls — reliable).
        if getattr(config, "STREAM_PRODUCTION_DETERMINISTIC_STATEMENTS", True):
            msg = compose_statement(batch, sb_info)
            return self._clip(msg) if msg else None

        # Optional legacy LLM path (off by default).
        if getattr(config, "OPENAI_DISABLED", False) or not getattr(
            config, "STREAM_PRODUCTION_USE_LLM_FOR_BATCH", True
        ):
            msg = compose_statement(batch, sb_info)
            return self._clip(msg) if msg else None
        try:
            from api.chat_utils import send_prompt_to_openai_system_user

            loop = asyncio.get_event_loop()
            system, user = build_summary_prompt(
                batch,
                sc2_context=self._sc2_context(),
                scoreboard_context=(sb_info or {}).get("text"),
            )
            resp = await loop.run_in_executor(
                None, send_prompt_to_openai_system_user, system, user
            )
            text = extract_llm_text(resp)
            if text:
                return self._clip(text)
            msg = compose_statement(batch, sb_info)
            return self._clip(msg) if msg else None
        except Exception as e:
            logger.error(f"stream production LLM summarize failed: {e}")
            msg = compose_statement(batch, sb_info)
            return self._clip(msg) if msg else None

    def _scoreboard_sources(self):
        """(label, rel_path, parser) for each configured, enabled scoreboard source."""
        sources = []
        csv_path = getattr(config, "STREAM_PRODUCTION_TEAMLEAGUE_CSV_PATH", "")
        if csv_path:
            sources.append(("teamleague", csv_path, "csv"))
        json_path = getattr(config, "STREAM_PRODUCTION_CUSTOM_SCOREBOARD_PATH", "")
        if json_path:
            sources.append(("custom", json_path, "json"))
        return sources

    def _spotlight_players(self, batch: FlushBatch):
        """Introed names that are players (not team names) in this burst."""
        snap = batch.snapshot
        a_name, b_name = snap.team_names() if snap else (None, None)
        team_names = {n for n in (a_name, b_name) if n}
        out = []
        for e in batch.events:
            if e.type == "intro":
                p = e.data.get("player")
                if p and p not in team_names and p not in out:
                    out.append(p)
        return out

    def _fetch_parse_scoreboard(self, rel_path: str, kind: str):
        if kind == "csv":
            text = self.client.fetch_path_text(rel_path)
            return parse_teamleague_csv(text).get("matchups", []) if text else []
        obj = self.client.fetch_path_json(rel_path)
        return parse_custom_scoreboard(obj).get("matchups", []) if obj else []

    async def _resolve_scoreboard_info(self, batch: FlushBatch) -> Optional[dict]:
        """Fetch the configured scoreboards, detect which one changed, and return the
        relevant matchup as structured data (preferring the row that just changed):
        {kind, a, sa, b, sb, game_winner, text}.

        Triggered on score/winner OR a bare GG: custom games update the custom JSON and
        fire a GG/intro but NO team-league `score` event, so a GG must also probe the
        scoreboards to detect a custom-game change."""
        counts = batch.event_type_counts()
        if not (counts.get("score") or counts.get("winner") or counts.get("gg")):
            return None
        if not getattr(config, "STREAM_PRODUCTION_USE_SCOREBOARDS", True):
            return None

        loop = asyncio.get_event_loop()
        spotlight = self._spotlight_players(batch)
        changed = []   # (label, winner-known dict) from changed_with_winner
        fallback = []  # (label, matchup) matching the spotlighted player

        for label, rel_path, kind in self._scoreboard_sources():
            curr = await loop.run_in_executor(None, self._fetch_parse_scoreboard, rel_path, kind)
            if not curr:
                continue
            prev = self._prev_scoreboards.get(rel_path, [])
            for info in changed_with_winner(prev, curr):
                changed.append((label, info))
            for p in spotlight:
                m = find_matchup_for_player(curr, p)
                if m:
                    fallback.append((label, m))
            self._prev_scoreboards[rel_path] = curr

        if changed:
            # Prefer the changed row that involves a spotlighted player.
            label, info = next(
                (c for c in changed if any(c[1]["matchup"].has_player(p) for p in spotlight)),
                changed[0],
            )
            m = info["matchup"]
            return {
                "kind": label,  # "teamleague" or "custom" — which scoreboard actually changed
                "a": m.a, "sa": m.score_a, "b": m.b, "sb": m.score_b,
                "game_winner": info["winner"],
                "text": describe_matchup_record(
                    m, info["winner"], info["winner_score"], info["loser"], info["loser_score"]
                ),
            }
        if fallback:
            label, m = fallback[0]
            return {
                "kind": label,
                "a": m.a, "sa": m.score_a, "b": m.b, "sb": m.score_b,
                "game_winner": None,
                "text": describe_matchup_record(m),
            }
        return None

    def _sc2_context(self) -> Optional[str]:
        """Best-effort fusion: what 1v1 the SC2 client most recently saw.

        Only supplements the LLM prompt; never forced into a deterministic line,
        since mapping a single 1v1 to a team-score point is not reliable.
        """
        try:
            gs = getattr(self.bot_core, "game_state", None) if self.bot_core else None
            game = gs.get_last_game_result() if gs else None
            if not game or not hasattr(game, "get_player_names"):
                return None
            names = game.get_player_names()
            if not names:
                return None
            winner = game.get_winner() if hasattr(game, "get_winner") else None
            base = "most recent 1v1: " + " vs ".join(names)
            return f"{base} (winner: {winner})" if winner else base
        except Exception:
            return None

    async def _emit_chat(self, message: str):
        tb = self._twitch_bot()
        if not tb or not hasattr(tb, "send_channel_message_sync"):
            logger.warning("stream production: no Twitch bot to emit message")
            return
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, tb.send_channel_message_sync, message)
            logger.info(f"[stream-production] said: {message}")
        except Exception as e:
            logger.error(f"stream production chat emit failed: {e}")

    def _twitch_bot(self):
        if not self.bot_core:
            return None
        svc = self.bot_core.chat_services.get("twitch")
        return getattr(svc, "twitch_bot", None) if svc else None

    def _clip(self, text: Optional[str]) -> str:
        if not text:
            return ""
        lim = int(getattr(config, "TWITCH_CHAT_BYTE_LIMIT", 450) or 450)
        raw = text.encode("utf-8")
        if len(raw) <= lim:
            return text
        return raw[:lim].decode("utf-8", errors="ignore").rstrip()

    # --- logging ----------------------------------------------------------

    def _log_raw_events(self, snapshot):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = []
        for e in snapshot.recent_events:
            lines.append(f"{ts} | seq={snapshot.seq} | RAW {e.type} #{e.id} {e.data}")
        self._append_log("\n".join(lines))

    def _log_batch(self, batch: FlushBatch):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        counts = batch.event_type_counts()
        summary = " ; ".join(batch.lines) if batch.lines else "(no significant change)"
        self._append_log(
            f"{ts} | FLUSH events={counts} significant={batch.significant} "
            f"batch={batch.is_batch} -> {summary}"
        )

    def _append_log(self, text: str):
        if not text:
            return
        try:
            if os.path.exists(self.activity_log) and os.path.getsize(self.activity_log) > MAX_LOG_SIZE:
                with open(self.activity_log, "r", encoding="utf-8") as f:
                    existing = f.readlines()
                keep = existing[len(existing) // 2:]
                with open(self.activity_log, "w", encoding="utf-8") as f:
                    f.write(f"--- log rolled over at {datetime.now()} ---\n")
                    f.writelines(keep)
            with open(self.activity_log, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except Exception as e:
            logger.debug(f"stream production log write failed: {e}")
