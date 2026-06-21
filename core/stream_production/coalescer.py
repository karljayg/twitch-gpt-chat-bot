"""Anti-spam coalescing for Stream Production events.

Pipeline: raw events -> Reducer (collapse a burst to net "canonical lines")
-> EventCoalescer (debounce window + cooldown so 2+ updates in quick succession
become ONE Mathison statement) -> summary prompt builder (LLM only for batches).

The coalescer is poll-driven and time-injectable so it is unit-testable without
real clocks or network: the adapter calls add() then poll() each cycle.
"""
import logging
from typing import List, Optional

import settings.config as config
from core.stream_production.models import StatusSnapshot, StreamEvent

logger = logging.getLogger(__name__)

# Logged for the activity file but never chat-worthy on their own.
_NOISE_TYPES = {"connect", "music"}

_DEFAULT_MEANINGFUL_SCENES = ["pog", "scoreboard", "custom-scoreboard"]


def _cfg(explicit, key, default):
    if explicit is not None:
        return explicit
    return getattr(config, key, default)


def _last_of(events: List[StreamEvent], type_: str) -> Optional[StreamEvent]:
    for e in reversed(events):
        if e.type == type_:
            return e
    return None


def _dedupe(items):
    seen = set()
    out = []
    for it in items:
        if it in seen:
            continue
        seen.add(it)
        out.append(it)
    return out


class Reducer:
    """Collapse a batch of raw events into canonical one-line strings.

    Only *materially significant* changes survive; transient noise (bare scene
    flips, music, connects) is dropped. Score events collapse to a net delta so
    three rapid bumps read as one fact. Team-league aware: the API `score`/`match`
    values are the authoritative team aggregate (the big top-line score).
    """

    def __init__(self, meaningful_scenes=None):
        self.meaningful_scenes = set(
            _cfg(meaningful_scenes, "STREAM_PRODUCTION_MEANINGFUL_SCENES", _DEFAULT_MEANINGFUL_SCENES)
        )

    def reduce(self, events: List[StreamEvent], snapshot: StatusSnapshot) -> List[str]:
        if not events or snapshot is None:
            return []
        lines: List[str] = []

        winner_ev = _last_of(events, "winner")
        if winner_ev:
            lines.append(self._winner_line(winner_ev, snapshot))

        # Score: only when the series is not already being announced as decided.
        score_evs = [e for e in events if e.type == "score"]
        if score_evs and not winner_ev:
            line = self._score_line(score_evs, snapshot)
            if line:
                lines.append(line)

        # Intros are ONLY meaningful when tied to a GG/match-GG (or a decided series):
        # that combination means the spotlighted player just won their game. A bare
        # intro with no GG is just an intro and is not worth a Mathison line.
        gg_ev = _last_of(events, "gg")
        if gg_ev is not None or winner_ev:
            intro_line = self._intro_line(events, snapshot)
            if intro_line:
                lines.append(intro_line)

        # NOTE: scene changes are intentionally NOT emitted — "now showing the
        # scoreboard" is not meaningful commentary. Match-GG is handled via the
        # winner/series_winner signal, not as a standalone line, because a match-GG
        # only means the final game finished, not who won the series.
        return lines

    def _intro_line(self, events: List[StreamEvent], snapshot: StatusSnapshot) -> Optional[str]:
        """Collapse intro events. The feed introduces a player AND their team name;
        classify each against the known team names so we don't credit a team as a
        player (and never imply an intro is an upcoming opponent)."""
        intro_evs = [e for e in events if e.type == "intro"]
        if not intro_evs:
            return None
        a_name, b_name = snapshot.team_names()
        team_names = {n for n in (a_name, b_name) if n}
        players, teams = [], []
        for e in intro_evs:
            p = e.data.get("player")
            if not p:
                continue
            (teams if p in team_names else players).append(p)
        players = _dedupe(players)
        teams = _dedupe(teams)
        if players:
            label = ", ".join(players)
            if teams:
                label += f" ({teams[0]})"
            return f"Player spotlight: {label}"
        if teams:
            return f"Team spotlight: {teams[0]}"
        return None

    def _winner_line(self, winner_ev: StreamEvent, snapshot: StatusSnapshot) -> str:
        name = winner_ev.data.get("name") or snapshot.team_name_for(winner_ev.data.get("team"))
        a_name, b_name = snapshot.team_names()
        a_score, b_score = snapshot.team_scores()
        if name and a_name and b_name and a_score is not None and b_score is not None:
            return f"Series decided: {name} wins it ({a_name} {a_score}-{b_score} {b_name})"
        if name:
            return f"Series decided: {name} wins the match"
        return "Series decided"

    def _score_line(self, score_evs: List[StreamEvent], snapshot: StatusSnapshot) -> Optional[str]:
        # Per team: earliest 'from' and latest 'to' across the burst.
        first_from = {}
        last_to = {}
        for e in score_evs:
            t = e.data.get("team")
            if t is None:
                continue
            if t not in first_from:
                first_from[t] = e.data.get("from")
            last_to[t] = e.data.get("to")

        a_name, b_name = snapshot.team_names()
        names = {"a": a_name or "Team A", "b": b_name or "Team B"}

        moved = []
        for t in ("a", "b"):
            if t in first_from and first_from[t] != last_to[t]:
                moved.append((names[t], last_to[t]))
        if not moved:
            return None

        if len(moved) == 1:
            head = f"{moved[0][0]} score is now {moved[0][1]}"
        else:
            head = "Scores: " + ", ".join(f"{n} now {to}" for n, to in moved)

        # Always show the full team-league tally so the line stands alone.
        a_score, b_score = snapshot.team_scores()
        tail = ""
        if a_score is not None and b_score is not None:
            tail = f" ({names['a']} {a_score} - {b_score} {names['b']})"
        return head + tail


class FlushBatch:
    """A settled burst ready to be turned into one statement."""

    def __init__(self, events: List[StreamEvent], snapshot: StatusSnapshot, lines: List[str]):
        self.events = events
        self.snapshot = snapshot
        self.lines = lines

    @property
    def significant(self) -> bool:
        return bool(self.lines)

    @property
    def is_batch(self) -> bool:
        return len(self.lines) >= 2

    def event_type_counts(self) -> dict:
        counts: dict = {}
        for e in self.events:
            counts[e.type] = counts.get(e.type, 0) + 1
        return counts


class EventCoalescer:
    """Debounce buffer with a cooldown floor.

    - QUIET window: flush after this much silence (each new event resets it) so a
      slow manual score-update burst lands as one message.
    - MAX window: hard cap from the first buffered event so a continuous trickle
      still eventually speaks.
    - WINNER quiet: a series-deciding `winner` uses a shorter window (speak fast,
      but still scoop up a near-simultaneous final score tick).
    - COOLDOWN: minimum gap between flushes; events arriving during cooldown keep
      buffering and roll into the next statement.
    """

    def __init__(self, reducer=None, quiet=None, max_window=None, winner_quiet=None, cooldown=None):
        self.reducer = reducer or Reducer()
        self.quiet = _cfg(quiet, "STREAM_PRODUCTION_QUIET_WINDOW_SECONDS", 20)
        self.max_window = _cfg(max_window, "STREAM_PRODUCTION_MAX_WINDOW_SECONDS", 60)
        self.winner_quiet = _cfg(winner_quiet, "STREAM_PRODUCTION_WINNER_QUIET_WINDOW_SECONDS", 5)
        self.cooldown = _cfg(cooldown, "STREAM_PRODUCTION_COOLDOWN_SECONDS", 30)
        self._pending: List[StreamEvent] = []
        self._first_at: Optional[float] = None
        self._last_at: Optional[float] = None
        self._cooldown_until: float = 0.0
        self._latest_snapshot: Optional[StatusSnapshot] = None
        self._seen_keys = set()

    def prime_seen(self, events) -> None:
        """Mark events as already-seen WITHOUT buffering them.

        Used at startup so a bot restart mid-match does not re-announce the
        events that were already in the feed before we connected.
        """
        for e in events or []:
            self._seen_keys.add(e.dedup_key())

    def add(self, events, snapshot, now: float) -> int:
        """Buffer any new events. Returns the count of genuinely-new events added."""
        if snapshot is not None:
            self._latest_snapshot = snapshot
        added = 0
        for e in events or []:
            key = e.dedup_key()
            if key in self._seen_keys:
                continue
            self._seen_keys.add(key)
            self._pending.append(e)
            added += 1
            if self._first_at is None:
                self._first_at = now
            self._last_at = now
        if len(self._seen_keys) > 5000:
            # Keep memory bounded; older keys are safe to forget.
            self._seen_keys = set(list(self._seen_keys)[-2000:])
        return added

    def poll(self, now: float) -> Optional[FlushBatch]:
        """Return a FlushBatch when the buffer is ready to speak, else None."""
        if not self._pending:
            return None
        if now < self._cooldown_until:
            return None
        quiet = self.winner_quiet if self._has_winner() else self.quiet
        quiet_ok = self._last_at is not None and (now - self._last_at) >= quiet
        max_ok = self._first_at is not None and (now - self._first_at) >= self.max_window
        if not (quiet_ok or max_ok):
            return None
        return self._flush(now)

    def _has_winner(self) -> bool:
        return any(e.type == "winner" for e in self._pending)

    def _flush(self, now: float) -> FlushBatch:
        events = self._pending
        snapshot = self._latest_snapshot
        try:
            lines = self.reducer.reduce(events, snapshot) if snapshot is not None else []
        except Exception as e:
            logger.error(f"stream production reduce failed: {e}")
            lines = []
        batch = FlushBatch(events, snapshot, lines)
        self._pending = []
        self._first_at = None
        self._last_at = None
        self._cooldown_until = now + self.cooldown
        return batch


# --- Summarization (LLM only for multi-line batches) -------------------------

_SUMMARY_SYSTEM = (
    "You are Mathison, a StarCraft 2 broadcast co-host for an FSL TEAM-LEAGUE match. "
    "Two teams face each other; each point is one player's 1v1 win, and the team score "
    "is the running tally of points. You are given factual production events that just "
    "happened on the broadcast. Write ONE short, natural spoken-style line for Twitch chat.\n"
    "How to read the facts:\n"
    "- A 'score' is the TEAM tally (e.g. PulledTheBoys 6 - 7 PSIOP Gaming). Always frame "
    "it as both teams and note who leads or how close it is.\n"
    "- A 'Player spotlight' is a player shown on stream. Right after a game/GG it is almost "
    "always the player who just WON their point, so credit them (e.g. 'well played <player>').\n"
    "- A name in parentheses after a player is that player's TEAM, not an opponent.\n"
    "- A 'head-to-head' line gives a real per-player record with each number bound to a named "
    "player (e.g. 'NukLeo: 2, Neutrophil: 4 (Neutrophil leads 4-2)'). If it names the spotlighted "
    "player you SHOULD cite it.\n"
    "HARD RULES:\n"
    "- Use ONLY the facts given. NEVER invent an opponent, a per-player score, a map, or who "
    "anyone plays next.\n"
    "- When you cite a head-to-head, keep EACH number with the exact player it is labeled to. "
    "NEVER swap or reverse them. If the fact says 'Neutrophil: 4, NukLeo: 2', then Neutrophil has 4 "
    "and NukLeo has 2 — even if NukLeo just won this game. Respect the stated leader.\n"
    "- The two teams are already playing each other. NEVER say a team is 'about to take on' or "
    "'face' another team 'next'.\n"
    "- Do not confuse a player name with a team name.\n"
    "- Concise (max ~35 words), no emojis, no hashtags, no @mentions. Sound like a caster, "
    "not a data label."
)


def format_featured_matchups(custom_scoreboard: Optional[dict]) -> Optional[str]:
    """Turn data/custom_scoreboard.json into 'PlayerA s-s PlayerB' text, or None."""
    if not custom_scoreboard:
        return None
    matches = custom_scoreboard.get("matches") or []
    out = []
    for m in matches:
        a, b = m.get("a"), m.get("b")
        sa, sb = m.get("scoreA"), m.get("scoreB")
        if a and b and sa is not None and sb is not None:
            out.append(f"{a} {sa}-{sb} {b}")
    return "; ".join(out) if out else None


def build_summary_prompt(
    batch: FlushBatch,
    sc2_context: Optional[str] = None,
    scoreboard_context: Optional[str] = None,
):
    """Return (system_text, user_text) for a batched (2+) summary LLM call."""
    facts = "\n".join(f"- {ln}" for ln in batch.lines)
    user = f"Team-league production update (most recent burst):\n{facts}"

    counts = batch.event_type_counts()
    if counts.get("gg") and not counts.get("winner"):
        user += "\n\nContext: a game just finished (a GG was shown)."

    if scoreboard_context:
        user += (
            f"\n\nScoreboard head-to-head (authoritative; each number is bound to its named player "
            f"— keep them exactly, do not reverse): {scoreboard_context}. If it names the spotlighted "
            f"player above, cite that head-to-head accurately. If none name the spotlighted player, "
            f"ignore this entirely and do not mention these names."
        )

    if sc2_context:
        user += (
            f"\n\nSC2 client context (use ONLY if it is clearly the same game just played; "
            f"do not force it, and never invent a head-to-head count): {sc2_context}"
        )
    return _SUMMARY_SYSTEM, user


def _spotlight_from_events(events, snapshot) -> list:
    """Introed names that are players (not team names)."""
    a_name, b_name = snapshot.team_names() if snapshot else (None, None)
    team_names = {n for n in (a_name, b_name) if n}
    out = []
    for e in events:
        if e.type == "intro":
            p = e.data.get("player")
            if p and p not in team_names and p not in out:
                out.append(p)
    return out


def _h2h_phrase(scoreboard: Optional[dict]) -> Optional[str]:
    """Deterministic, flip-proof head-to-head: leader computed from the numbers."""
    if not scoreboard:
        return None
    a, sa, b, sb = scoreboard.get("a"), scoreboard.get("sa"), scoreboard.get("b"), scoreboard.get("sb")
    if not a or not b or sa is None or sb is None:
        return None
    if sa == sb:
        return f"head-to-head tied {sa}-{sa}"
    leader, hi, lo = (a, sa, sb) if sa > sb else (b, sb, sa)
    return f"{leader} leads the head-to-head {hi}-{lo}"


def _period(s: Optional[str]) -> Optional[str]:
    if not s:
        return s
    return s if s.endswith((".", "!", "?")) else s + "."


def _join(parts) -> str:
    return " ".join(p for p in parts if p)


def _compose_custom(batch: FlushBatch, sb: dict) -> Optional[str]:
    """Custom-game line: just the two players + their match score, no team names."""
    a, sa, b, sb_score = sb.get("a"), sb.get("sa"), sb.get("b"), sb.get("sb")
    if not a or not b:
        return None
    spotlight = _spotlight_from_events(batch.events, batch.snapshot)
    winner = sb.get("game_winner") or (spotlight[0] if spotlight else None)
    score_line = f"{a} {sa}-{sb_score} {b}" if sa is not None and sb_score is not None else None
    if winner and score_line:
        return f"{winner} takes the game. {score_line}."
    if winner:
        return f"{winner} takes the game."
    if score_line:
        return f"{score_line}."
    return None


def compose_statement(batch: FlushBatch, scoreboard: Optional[dict] = None) -> Optional[str]:
    """Build a concise, fully deterministic statement — no LLM judgment calls.

    Winner, team score, and who-leads are all derived from the data, so the score
    can't be flipped. Returns None when there's nothing meaningful to say.
    """
    snap = batch.snapshot
    if snap is None:
        return None
    events = batch.events
    counts = batch.event_type_counts()

    # Custom (non-team-league) game: the active scoreboard is the custom JSON, which is
    # a 1v1 between two players. Use ONLY those players + their score — no team names,
    # team totals, or "wins for <team>" (that's team-league-only data).
    if scoreboard and scoreboard.get("kind") == "custom":
        return _compose_custom(batch, scoreboard)

    a_name, b_name = snap.team_names()
    a_score, b_score = snap.team_scores()
    tally = None
    if a_name and b_name and a_score is not None and b_score is not None:
        tally = f"{a_name} {a_score}-{b_score} {b_name}"

    spotlight = _spotlight_from_events(events, snap)
    game_winner = (scoreboard or {}).get("game_winner") or (spotlight[0] if spotlight else None)
    h2h = _period(_h2h_phrase(scoreboard))

    # --- Series decided (authoritative: a transient `winner` event in THIS batch) ---
    # Do NOT use snap.series_winner(): it is a persistent field that stays set after a
    # series ends, which mislabels later games as series wins. A match-GG alone is also
    # not a series win — it only means the final game of the match finished.
    winner_ev = _last_of(events, "winner")
    if winner_ev:
        series_team = winner_ev.data.get("name") or snap.team_name_for(winner_ev.data.get("team"))
        winner_side = winner_ev.data.get("team")
        # Only credit a clinching player if the point just scored was for the winning
        # team — otherwise the spotlighted player is on the losing side.
        scored_for_winner = any(
            e.type == "score" and e.data.get("team") == winner_side for e in events
        )
        if game_winner and scored_for_winner and series_team:
            head, tail = f"{game_winner} takes the series for {series_team}!", h2h
        elif series_team:
            head, tail = f"{series_team} wins the series!", None
        else:
            head, tail = None, None
        body = f"The score is {tally}." if tally else None
        return _join([head, body, tail]) or None

    # --- A game finished and a point was scored ---
    score_evs = [e for e in events if e.type == "score"]
    if counts.get("gg") and (score_evs or game_winner):
        winner_team = snap.team_name_for(score_evs[-1].data.get("team")) if score_evs else None
        if game_winner and winner_team:
            head = f"{game_winner} wins for {winner_team}" + (f", making it {tally}." if tally else ".")
        elif game_winner:
            # No team-league score event -> don't trust the snapshot's team tally
            # (it may be stale team-league data during a custom game).
            head = f"{game_winner} takes the game."
        else:
            head = "A game just finished." + (f" {tally}." if tally else "")
        return _join([head, h2h]) or None

    # --- Bare team-score change (manual correction, no GG) ---
    if score_evs:
        line = _period(Reducer()._score_line(score_evs, snap))
        return _join([line, h2h]) or None

    # --- Fallback: whatever the reducer found (deterministic) ---
    if batch.lines:
        return _join(_period(l) for l in batch.lines) or None
    return None


def extract_llm_text(response) -> Optional[str]:
    """Pull plain text out of an OpenAI chat completion (new or legacy shape)."""
    try:
        return (response.choices[0].message.content or "").strip()
    except Exception:
        try:
            return (response.choices[0].message["content"] or "").strip()
        except Exception:
            return None
