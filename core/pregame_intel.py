"""
Pre-game intel: gather facts into PreGameBrief, then run_known_opponent_pregame executes
saved-notes formatting → pattern/ML check (always when DB available) → ML chat line only if no formatted notes
→ last-meeting LLM → optional DB build LLM (skipped when notes or strong pattern/learning intel) → optional GLHF line → record.

Uses conversation_mode \"last_time_played\" for factual OpenAI lines (no mood/perspective).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from settings import config
from api.chat_utils import (
    format_expert_notes_for_last_meeting_prompt,
    format_saved_notes_for_direct_chat,
    processMessageForOpenAI,
    msgToChannel,
    substitute_streamer_aliases_for_chat_display,
    twitch_notes_from_saved_comments,
)
from api.ml_opponent_analyzer import get_ml_analyzer
from utils.time_utils import parse_game_duration_seconds_from_summary


@dataclass
class PreGameBrief:
    """Facts for known-opponent pre-game (after alias resolution)."""

    opponent_display_name: str
    opponent_race: str
    streamer_current_race: str
    streamer_race_compare: str
    today_streamer_race: str
    today_opponent_race: str
    db_result: Dict[str, Any]
    how_long_ago: str
    record_vs: Optional[Tuple[int, int]]
    player_comments: List[Any]
    first_few_build_steps: Optional[List[str]]
    # SC2 / DB spellings for head-to-head lookup (e.g. ladder name + alias); empty → display name only
    opponent_lookup_hints: Tuple[str, ...] = field(default_factory=tuple)
    # Rare: fold saved notes into one LLM user message (tests / special callers). Preview/review uses False:
    # expert Player_Comments: direct chat uses name — body; bundled preview wraps body for LLM (casual framing).
    inline_saved_notes_in_last_meeting: bool = False
    # Ladder Random: separate DB rows per Terran/Zerg/Protoss (replay race is never "Random")
    random_race_intel: Tuple[
        Tuple[str, Dict[str, Any], List[Any], Optional[List[str]]], ...
    ] = field(default_factory=tuple)
    # Set by run_known_opponent_pregame when DB opening is appended verbatim after the LLM line.
    suppress_opponent_training_narrative: bool = False


def _streamer_accounts_lower() -> List[str]:
    return [str(n).lower() for n in config.SC2_PLAYER_ACCOUNTS]


def _replay_summary_omit_build_step_tables(text: str) -> str:
    """Remove build-order dumps from replay text so bundled preview cannot echo step lists."""
    if not text or not isinstance(text, str):
        return text
    marker = "\n[Build order steps omitted — use abbreviated list at end of prompt only.]\n"
    cur = text
    cur = re.sub(
        r"(?im)^[^\n]{0,200}build order[^\n]*\n(?:^[ \t]*Time:.*\n)+",
        marker,
        cur,
    )
    cur = re.sub(
        r"(?is)build order\s*:.*?(?=\n\s*(?:Winners|Losers|Units Lost|Game Duration)|\Z)",
        marker,
        cur,
    )
    out_lines: List[str] = []
    for ln in cur.splitlines():
        if re.search(r"\bat\s+\d{1,2}:\d{2}\b", ln, re.I):
            low = ln.lower()
            if any(x in low for x in ("game duration", "played at", "duration:")):
                out_lines.append(ln)
                continue
            continue
        out_lines.append(ln)
    return "\n".join(out_lines)


_TRAINED_OMIT = "\n[Unit training tallies omitted — never quote or paraphrase them.]\n"


def _replay_summary_strip_units_lost_blocks(text: str) -> str:
    """
    Remove ``Units Lost by {player}`` tables from replay text.

    Opponent preview must not quote loss tallies — models often mis-attribute rows to the streamer
    (e.g. opponent Protoss losses described as the streamer 'lost probes/zealots').
    Winners/Losers lines stay for who won.
    """
    if not text or not isinstance(text, str):
        return text
    # Header + one or more lines "Thing: count" (building/unit lost tallies from replay summary)
    block = re.compile(
        r"(?ms)^Units Lost by [^\n]+\n(?:^[ \t]*[^\n:]+:\s*\d+\s*\n)+",
    )
    cur = text
    while True:
        nxt = block.sub("", cur, count=1)
        if nxt == cur:
            break
        cur = nxt
    return cur


def _replay_summary_sanitize_for_inline_prompt(text: str) -> str:
    """
    Strip replay blobs that bundled preview must not echo (Players/Map/Timestamp noise,
    per-player 'Name trained:' tallies, Units Lost tables). Keeps Winners/Losers and Game Duration when present.
    """
    if not text or not isinstance(text, str):
        return text
    cur = _replay_summary_strip_units_lost_blocks(text)
    map_hint = ""
    m_map = re.search(
        r"(?i)\bMap:\s*([^\n]+?)(?:\s*(?:Region:|Timestamp:|Winners:)|\n|\Z)",
        cur,
    )
    if m_map:
        map_hint = f"[Last game map from archive: {m_map.group(1).strip()}]\n"
    if re.search(r"(?i)\bPlayers:\s", cur) and re.search(r"(?i)\bWinners:\s", cur):
        cur = re.sub(r"(?is)\bPlayers:\s*.+?(?=\bWinners:)", "", cur)
    cur = re.sub(r"(?i)\s*Timestamp:\s*\d+\s*", " ", cur)
    cur = re.sub(r"(?i)\s*Region:\s*\S+\s*", " ", cur)
    cur = re.sub(r"(?i)\s*Game Type:\s*[^\n]+\s*", " ", cur)
    # Per-line: '.' must not swallow Game Duration / following replay lines (trained blobs can
    # sit on the same line as Winners/Losers).
    # Some replays use "Name trained: ..." others "Name trained unit, unit" (no colon).
    _trained_seg = re.compile(
        r"(?i)\b\S+?\s+trained(?:\s+|:)\s*.*?(?=\s+\S+?\s+trained(?:\s+|:)|\Z)"
    )
    out_lines: List[str] = []
    for ln in cur.splitlines():
        seg_ln = ln
        for _ in range(32):
            nxt = _trained_seg.sub(_TRAINED_OMIT.strip(), seg_ln, count=1)
            if nxt == seg_ln:
                break
            seg_ln = nxt
        out_lines.append(seg_ln)
    cur = "\n".join(out_lines)
    cur = re.sub(
        r"(?i)(?:\s*\[Unit training tallies omitted[^\]]*\]\s*)+",
        _TRAINED_OMIT,
        cur,
    )
    if map_hint:
        cur = map_hint + cur
    return _replay_summary_omit_build_step_tables(cur)


def supplement_player_comments_from_db_row(
    db_result: Optional[Dict[str, Any]],
    player_comments: Optional[List[Any]],
) -> List[Any]:
    """
    get_player_comments() can omit the primary replay row (e.g. legacy duration filter skew).
    Ensures Player_Comments on the chosen analysis row appears in chat / inline preview.
    """
    rows = list(player_comments or [])
    if not db_result:
        return rows
    raw = (db_result.get("Player_Comments") or db_result.get("player_comments") or "").strip()
    if not raw:
        return rows
    for c in rows:
        note = (c.get("player_comments") or c.get("Player_Comments") or "").strip()
        if note == raw:
            return rows
    dp = db_result.get("Date_Played")
    if hasattr(dp, "strftime"):
        dp_str = dp.strftime("%Y-%m-%d %H:%M:%S")
    elif dp is None:
        dp_str = ""
    else:
        dp_str = str(dp)
    rows.insert(
        0,
        {
            "player_comments": raw,
            "Player_Comments": raw,
            "map": db_result.get("Map", "") or "",
            "date_played": dp_str,
        },
    )
    return rows


def prev_streamer_race_from_row(db_result: Dict[str, Any]) -> str:
    prev_player1_name = db_result.get("Player1_Name", "")
    prev_player1_race = db_result.get("Player1_Race", "")
    prev_player2_race = db_result.get("Player2_Race", "")
    acct = _streamer_accounts_lower()
    if str(prev_player1_name).lower() in acct:
        return str(prev_player1_race)
    return str(prev_player2_race)


_STEP_NAME_FROM_LINE = re.compile(r"(?i)\bName:\s*([^,\n]+)")
_MAX_RAW_STEP_CHARS = 400


def _coerce_step_to_unit_label(step: str) -> Optional[str]:
    """Normalize DB/replay lines to a single unit/building name for abbreviation."""
    if not step or not isinstance(step, str):
        return None
    s = step.strip()
    if len(s) > _MAX_RAW_STEP_CHARS:
        return None
    if " at " in s:
        left = s.split(" at ", 1)[0].strip()
        return left if left else None
    m = _STEP_NAME_FROM_LINE.search(s)
    if m:
        return m.group(1).strip()
    first = s.split(",", 1)[0].strip()
    if len(first) <= 80 and re.match(r"^[A-Za-z][A-Za-z0-9\s\-]{1,79}$", first):
        return first
    return None


def abbreviated_grouped_build_string(
    first_few_build_steps: Optional[List[str]],
    *,
    for_chat_suffix: bool = False,
) -> str:
    """
    Same grouping as ``compose_build_order_user_message`` — preserves strict training order
    (e.g. Drone x2, Pool, Hatch). ``for_chat_suffix`` applies Twitch length caps from config.
    """
    if not first_few_build_steps:
        return ""
    from utils.sc2_abbreviations import abbreviate_unit_name

    abbreviated_steps: List[str] = []
    for step in first_few_build_steps:
        label = _coerce_step_to_unit_label(step)
        if not label:
            continue
        abbreviated_steps.append(abbreviate_unit_name(label.strip()))

    grouped_build: List[str] = []
    prev_unit: Optional[str] = None
    count = 0
    for unit in abbreviated_steps:
        if not unit:
            continue
        if unit == prev_unit:
            count += 1
        else:
            if prev_unit:
                grouped_build.append(f"{prev_unit} x{count}" if count > 1 else prev_unit)
            prev_unit = unit
            count = 1
    if prev_unit:
        grouped_build.append(f"{prev_unit} x{count}" if count > 1 else prev_unit)

    if for_chat_suffix:
        max_groups = max(0, int(getattr(config, "PREGAME_OPENING_SUFFIX_MAX_GROUPS", 28)))
        max_chars = max(0, int(getattr(config, "PREGAME_OPENING_SUFFIX_MAX_CHARS", 220)))
        truncated_groups = bool(max_groups and len(grouped_build) > max_groups)
        if truncated_groups:
            grouped_build = grouped_build[:max_groups]
        pieces = list(grouped_build)
        out = ", ".join(pieces)
        truncated_chars = False
        if max_chars > 0 and len(out) > max_chars:
            while len(pieces) > 1 and len(", ".join(pieces)) > max_chars:
                pieces.pop()
                truncated_chars = True
            out = ", ".join(pieces)
            if len(out) > max_chars:
                out = out[: max_chars - 3].rstrip(", ") + " …"
                truncated_chars = True
            elif truncated_chars or truncated_groups:
                out += " …"
        elif truncated_groups:
            out += " …"
        return out

    return ", ".join(grouped_build)


def deterministic_opponent_opening_suffix(brief: PreGameBrief) -> str:
    """Verbatim ordered opening from DB extract (abbrev + grouping). Empty if nothing to say."""
    od = brief.opponent_display_name.strip()
    if brief.random_race_intel:
        parts: List[str] = []
        for race, _, _, steps in brief.random_race_intel:
            if not steps:
                continue
            s = abbreviated_grouped_build_string(steps, for_chat_suffix=True)
            if s:
                parts.append(f"{race}: {s}")
        if not parts:
            return ""
        return f"{od} opening ({' | '.join(parts)})"
    if brief.first_few_build_steps:
        s = abbreviated_grouped_build_string(brief.first_few_build_steps, for_chat_suffix=True)
        if not s:
            return ""
        return f"{od} opening: {s}"
    return ""


def _extract_map_display_from_summary(summary: str, fallback_map: str = "") -> str:
    if not summary:
        return str(fallback_map or "").strip()
    m_map = re.search(
        r"(?i)\bMap:\s*([^\n]+?)(?:\s*(?:Region:|Timestamp:|Winners:)|\n|\Z)",
        summary,
    )
    if m_map:
        return m_map.group(1).strip()
    return str(fallback_map or "").strip()


def _extract_duration_display_from_summary(summary: str) -> str:
    if not summary:
        return "the duration in the excerpt"
    m = re.search(r"(?i)Game\s+Duration:\s*([^\n]+)", summary)
    if m:
        return m.group(1).strip()
    secs = parse_game_duration_seconds_from_summary(summary)
    if secs is None:
        return "the duration in the excerpt"
    if secs >= 3600:
        h, r = divmod(secs, 3600)
        m, s = divmod(r, 60)
        return f"{h}h {m}m {s}s"
    if secs >= 60:
        m, s = divmod(secs, 60)
        return f"{m}m {s}s"
    return f"{secs}s"


def _streamer_outcome_display_phrase(summary: str) -> str:
    nick = getattr(config, "STREAMER_NICKNAME", "Streamer")
    # Replay blobs often put Map/Region/Winners/Losers on one line — do not require ^Winners.
    mw = re.search(
        r"(?i)Winners:\s*([^\n]+?)(?=\s*(?:Losers:|Game\s+Duration)|\n|$)",
        summary or "",
    )
    ml = re.search(
        r"(?i)Losers:\s*([^\n]+?)(?=\s*(?:Game\s+Duration)|\n|$)",
        summary or "",
    )
    win_blob = (mw.group(1).strip() if mw else "") or ""
    lose_blob = (ml.group(1).strip() if ml else "") or ""

    def line_mentions_streamer(blob: str) -> bool:
        if not blob:
            return False
        if re.search(r"\b" + re.escape(nick) + r"\b", blob, re.I):
            return True
        for acct in getattr(config, "SC2_PLAYER_ACCOUNTS", []) or []:
            if re.search(r"\b" + re.escape(str(acct)) + r"\b", blob, re.I):
                return True
        return False

    if line_mentions_streamer(win_blob):
        return f"a win for {nick}"
    if line_mentions_streamer(lose_blob):
        return f"a loss for {nick}"
    return f"who won or lost for {nick} (from Winners/Losers in the excerpt)"


def compose_last_meeting_user_message(
    brief: PreGameBrief,
    *,
    bundled_saved_notes: bool = False,
    saved_notes_text: str = "",
) -> str:
    """OpenAI user message for last meeting line (last_time_played mode).

    bundled_saved_notes: True when the full prompt bundles expert player_comment text for the LLM
    (please preview / inline bundle). Strategy wording must follow those notes, not generic replay units.
    """
    prev_streamer_race = prev_streamer_race_from_row(brief.db_result)
    same_matchup = prev_streamer_race.lower() == brief.streamer_race_compare.lower()
    replay_snip = brief.db_result.get("Replay_Summary") or ""
    inline = getattr(brief, "inline_saved_notes_in_last_meeting", False)
    if isinstance(replay_snip, str) and inline:
        replay_snip = _replay_summary_sanitize_for_inline_prompt(replay_snip)
    elif isinstance(replay_snip, str):
        replay_snip = _replay_summary_strip_units_lost_blocks(replay_snip)
    if isinstance(replay_snip, str):
        replay_snip = substitute_streamer_aliases_for_chat_display(replay_snip)
    short_thr = int(getattr(config, "SHORT_LAST_GAME_DURATION_SECONDS", 120))
    prev_secs = parse_game_duration_seconds_from_summary(replay_snip)
    trivial_prev = prev_secs is not None and prev_secs <= short_thr

    if trivial_prev:
        return (
            "Very short prior game (use archive below only):\n"
            "Write ONE Twitch sentence (max 22 words).\n"
            "Do NOT name the map. Do NOT quote duration (no seconds/minutes).\n"
            "The archived game ended almost immediately — describe it as opponent quit early "
            "or left right away or similar varied wording.\n"
            f"Include roughly how long ago they last met (~{brief.how_long_ago}).\n"
            "Mention who won only if Winners/Losers is explicit below.\n"
            "Do NOT list units or builds.\n"
            "----- REPLAY ARCHIVE -----\n"
            f"{replay_snip}\n"
        )

    p1n = str(brief.db_result.get("Player1_Name", ""))
    p2n = str(brief.db_result.get("Player2_Name", ""))
    p1r = str(brief.db_result.get("Player1_Race", ""))
    p2r = str(brief.db_result.get("Player2_Race", ""))
    od = brief.opponent_display_name.strip().lower()
    if p1n.lower() == od:
        archive_opp_race = p1r
    elif p2n.lower() == od:
        archive_opp_race = p2r
    else:
        archive_opp_race = p2r or p1r

    random_opp = (
        str(brief.today_opponent_race).strip().lower() == "random"
        and bool(brief.random_race_intel)
    )
    opp_for_narr = archive_opp_race if random_opp else brief.today_opponent_race

    opener_ctx = ""
    if random_opp:
        opener_ctx = (
            "[For reading the archive only — do not quote this block in chat] "
            "Opponent queued Random; spawn race unknown until load. "
            f"Primary excerpt below = their most recent archived game as {archive_opp_race}. "
            "Further excerpts = other races when present.\n\n"
        )

    msg = opener_ctx + "Do these 2: \n"
    if not same_matchup:
        msg += (
            f"NOTE: The previous game was {prev_streamer_race}v{opp_for_narr}, "
            f"but TODAY's game is {brief.today_streamer_race}v{brief.today_opponent_race}. "
            f"When describing the previous game, use the CORRECT races from that game "
            f"(previous matchup was {prev_streamer_race}v{opp_for_narr}). "
        )
    sn = config.STREAMER_NICKNAME
    if brief.today_streamer_race == "Random":
        msg += f"Even though {sn} is Random, the last time "
    elif random_opp:
        msg += f"The last time (vs {brief.opponent_display_name}, archive race {archive_opp_race}) "
    else:
        msg += "The last time "
    map_disp = _extract_map_display_from_summary(
        replay_snip, fallback_map=str(brief.db_result.get("Map", "") or "")
    )
    dur_disp = _extract_duration_display_from_summary(replay_snip)
    outcome_disp = _streamer_outcome_display_phrase(replay_snip)
    notes_blob = str(saved_notes_text or "")
    notes_has_time = bool(notes_blob and re.search(r"\bago\b|~\d+\s*[hmwd]\b", notes_blob, re.I))
    notes_has_map = bool(map_disp and notes_blob and map_disp.lower() in notes_blob.lower())
    include_time = not (bundled_saved_notes and notes_has_time)
    include_map = bool(map_disp) and not (bundled_saved_notes and notes_has_map)
    detail_parts: List[str] = []
    if include_map:
        detail_parts.append(f"on {map_disp}")
    if include_time:
        detail_parts.append(f"about {brief.how_long_ago}")
    detail_clause = " ".join(detail_parts).strip()
    if detail_clause:
        last_meeting_fact_clause = f"was {detail_clause}, {outcome_disp} in {dur_disp}."
    else:
        last_meeting_fact_clause = f"{outcome_disp} in {dur_disp}."
    msg += (
        f"{last_meeting_fact_clause} "
        f"(These values are filled from the archive — use them in chat as plain words, never brace placeholders.)\n"
    )
    if inline:
        if bundled_saved_notes:
            msg += (
                "After fixed lines and your casual expert-strategy wording (verbatim DB phrases): add exactly ONE sentence "
                "(max 28 words). Facts only: roughly how long ago, game duration, who won. "
                "If expert lines already include the map name, omit the map here (say it once total). "
                "If expert lines already include relative time, omit it here (say it once total). "
                "If winner/duration/map/time are already covered by fixed lines + expert lines, do not add another fact sentence. "
                "Add at most ONE short sentence only when a core fact is still missing. "
                "Do not repeat unit names, build shorthand, or strategy wording already stated in expert lines.\n"
                "Do not repeat the opponent name back-to-back; use 'they' after first mention.\n"
                "One-shot style example:\n"
                "'KJ is 1-0 vs Chiewy, who went cannon to proxy gateway robo immortal. "
                "The last time was a win for KJ in 5m 50s on Celestial Enclave LE about 10 hours ago.'\n"
                f"Do not describe {sn}'s build or '{sn} trained'.\n"
                "Avoid 'Players:', timestamps, comma-chained archive dumps from the excerpt.\n"
                "Do not repeat the head-to-head opener lines. Write plain sentences — do not mention meta rules about naming.\n"
                "Never cite unit-loss tallies or who lost how many of which unit — excerpt may omit those on purpose.\n"
            )
        elif getattr(brief, "suppress_opponent_training_narrative", False):
            msg += (
                f"In the replay summary below, {sn} is the streamer; {brief.opponent_display_name} is the opponent. "
                "After the fixed opener lines: at most TWO short sentences (under 45 words combined). "
                "Focus on last meeting only: how long ago, map, duration, winner — omit opponent unit/build/training lists "
                "(those facts are handled outside this sentence).\n"
                f"Do not describe {sn}'s build or '{sn} trained'.\n"
                "Do not repeat the head-to-head opener lines.\n"
            )
        else:
            msg += (
                f"In the replay summary below, {sn} is the streamer. "
                f"{brief.opponent_display_name} is the opponent. "
                "Build-order step lists and unit-training tallies are removed from the excerpt — do NOT reconstruct, "
                "quote, or invent timestamps, supply chains, or any 'Name trained' lists from the archive.\n"
                f"If you mention a training/unit list at all, it MUST be for {brief.opponent_display_name} only — "
                f"never describe {sn}'s units as the opponent's build (saved notes and the Opponent opening block, if any, "
                f"describe {brief.opponent_display_name}).\n"
                "Avoid in the Twitch sentence: 'Players:', 'Timestamp:', "
                f"'{sn} trained', comma-chained building/unit counts, or pasting any line marked omitted below.\n"
                "After the fixed opener lines (copy exactly), at most TWO short sentences for the rest "
                "(under 40 words total). Do not repeat the head-to-head record — the opener already gave it. "
                f"Prefer 'they/them' for {brief.opponent_display_name} after the first mention of their name.\n"
                "Do not name the map twice across the two sentences; do not repeat the same unit list in both.\n"
            )
    else:
        msg += (
            f"In the replay summary below, {sn} is the streamer. "
            f"{brief.opponent_display_name} is the opponent. "
            "When mentioning units/buildings, make sure you correctly identify which player built them. "
            f"Look at the section headers (e.g., '{sn}'s Build Order' vs '{brief.opponent_display_name}'s Build Order'). "
        )
    if random_opp:
        msg += (
            "[Archive only — do not quote in chat] "
            f"In the primary excerpt {brief.opponent_display_name} was {archive_opp_race}; "
            "today they are Random on ladder — use each excerpt's header for race.\n"
        )
    elif same_matchup:
        msg += (
            f"RACE CONSTRAINT: {sn} is {brief.today_streamer_race}, "
            f"{brief.opponent_display_name} is {brief.today_opponent_race}. "
            "ONLY mention units that exist for these races. Do NOT mention units from other races. "
        )
    else:
        msg += (
            f"In the PREVIOUS game: {sn} was {prev_streamer_race}, "
            f"{brief.opponent_display_name} was {opp_for_narr}. Use these races. "
        )
    if bundled_saved_notes and inline:
        msg += (
            "Use the replay excerpt below only to confirm time ago, duration, and winner — "
            "not to re-describe the opponent's strategy when player_comment lines already do.\n"
        )
    elif not inline:
        msg += (
            "Write ONE sentence (max 24 words) for this part.\n"
            "Include ONLY: roughly how long ago, map name, game duration, who won.\n"
            "Prefer wording like 'The last time they played was about … ago on that map, a win or loss in that duration.' "
            f"— use 'they' once {brief.opponent_display_name} was already named above; do not repeat the full opponent name in this sentence.\n"
            "If a saved-notes paragraph appears earlier in this full prompt, do not repeat it verbatim; at most one short nod.\n"
            "Do NOT list units, buildings, builds, or armies (opening summarized separately).\n"
        )
    if inline and not bundled_saved_notes and not getattr(
        brief, "suppress_opponent_training_narrative", False
    ):
        msg += (
            "Do NOT list units, buildings, builds, or armies drawn only from the replay excerpt in sentence one "
            "when opening blocks already summarized them.\n"
        )
    if inline:
        msg += (
            "If any 'Time:' or ' at M:SS' build lines remain in the excerpt, IGNORE them completely.\n"
        )
    if not inline and getattr(brief, "suppress_opponent_training_narrative", False):
        msg += (
            "Do not summarize opponent buildings or unit training from the excerpt alone "
            "(use facts only from Winners/Losers/duration/map as needed).\n"
        )
    msg += "-----\n" + f" \n {replay_snip} \n"

    primary_rid = brief.db_result.get("ReplayId")
    if brief.random_race_intel:
        chunks: List[str] = []
        for race, row, _, _ in brief.random_race_intel:
            if primary_rid is not None and row.get("ReplayId") == primary_rid:
                continue
            extra = row.get("Replay_Summary") or ""
            if inline:
                extra = _replay_summary_sanitize_for_inline_prompt(extra)
            elif isinstance(extra, str):
                extra = _replay_summary_strip_units_lost_blocks(extra)
            if isinstance(extra, str):
                extra = substitute_streamer_aliases_for_chat_display(extra)
            chunks.append(
                f"----- Archived vs this opponent when they played as {race} "
                f"(separate game from primary excerpt) -----\n{extra}"
            )
        if chunks:
            msg += "\n\n" + "\n\n".join(chunks)
    return msg


def compose_build_order_user_message(opponent_display_name: str, first_few_build_steps: List[str]) -> str:
    """OpenAI user message for opponent build-from-DB extract (last_time_played)."""
    abbreviated_build_string = abbreviated_grouped_build_string(
        first_few_build_steps, for_chat_suffix=False
    )
    sn = config.STREAMER_NICKNAME
    msg = f"Opponent build focus — {opponent_display_name} only (not {sn}).\n"
    msg += (
        f"If you mention training at all, phrase it as '{opponent_display_name} trained …' "
        f"— never '{sn} trained' for this block.\n"
    )
    msg += f"Build order (abbreviated): {abbreviated_build_string}\n\n"
    msg += "Requirements:\n"
    msg += "1. List ONLY units/buildings/spells that appear in the build order above - do NOT guess or infer units not shown\n"
    msg += "2. State simple facts - do NOT speculate on purpose, intent, or strategy\n"
    msg += "3. Do NOT use phrases like 'for aggression', 'timing attack', 'all-in', 'pressure', 'rush', 'bust', or any intent guessing\n"
    msg += "4. Example outputs (CORRECT):\n"
    msg += "   - '2 base Baneling Nest, Zergling Speed, Zerglings'\n"
    msg += "   - '3 base Roach Warren, Roaches, Ravagers'\n"
    msg += "   - '2 base Stargate, Oracle, Adept'\n"
    msg += "5. Example outputs (WRONG - DO NOT DO THIS):\n"
    msg += "   - 'Fast expand into roach timing' (speculates intent)\n"
    msg += "   - 'Gateway expand into blink stalker pressure' (uses strategy terms)\n"
    msg += "   - '2 base banshee into mech turtle' (speculates purpose)\n"
    msg += f"6. DO NOT mention {sn}'s play - ONLY describe {opponent_display_name}'s build\n"
    msg += (
        "7. ONE sentence only, max 18 words total. Do not use: timestamps (0:00), the word 'Time:', "
        "comma-chained step dumps, listing more than 5 distinct unit/building names, bullet lists, "
        "or copying the raw list format. Summarize the opening pattern in plain prose like the CORRECT examples.\n"
    )
    msg += "8. Do NOT mention units that are NOT in the abbreviated build order above\n"
    return msg


def _analysis_supersedes_db_build_extract(analysis_data: Optional[Dict[str, Any]]) -> bool:
    """
    True when pattern-learning or aggregate saved-notes intel already covers opening well enough
    that the separate DB build-order LLM block should be omitted.
    """
    if not analysis_data:
        return False
    t = analysis_data.get("analysis_type")
    if t == "learning_data":
        return True
    if t == "pattern_matching":
        label_min = float(getattr(config, "STRATEGY_PATTERN_LABEL_MIN_SIMILARITY", 0.85))
        for p in analysis_data.get("matched_patterns") or []:
            try:
                sim = float(p.get("similarity", 0))
            except (TypeError, ValueError):
                continue
            if sim + 1e-12 >= label_min:
                return True
    return False


def format_record_line(record_vs: Tuple[int, int], opponent_display_name: str) -> Optional[str]:
    min_h2h = int(getattr(config, "MIN_HEAD_TO_HEAD_GAMES_TO_SHOW_RECORD", 2))
    yw, yl = record_vs
    if yw + yl < min_h2h:
        return None
    return f"{config.STREAMER_NICKNAME}'s record vs {opponent_display_name}: {yw}-{yl}."


def run_known_opponent_pregame(
    bot,
    brief: PreGameBrief,
    logger,
    context_history: list,
    current_map: str,
    *,
    quiet_when_no_build_extract: bool = False,
    db_override: Any = None,
) -> None:
    """
    Execute pre-game messaging for a known DB opponent in fixed order.
    Mirrors game_started_handler streamer-vs-opponent branch behavior.
    """
    import logging

    log = logger or logging.getLogger(__name__)

    db = db_override if db_override is not None else getattr(bot, "db", None)

    brief.player_comments = supplement_player_comments_from_db_row(
        getattr(brief, "db_result", None),
        brief.player_comments,
    )

    ml_analysis_ran = False
    deferred_notes_text = ""
    raw_notes_text = ""

    if brief.player_comments:
        sorted_comments = sorted(
            brief.player_comments, key=lambda x: x.get("date_played", ""), reverse=True
        )
        raw_notes_text = (twitch_notes_from_saved_comments(sorted_comments, brief.opponent_display_name) or "").strip()
        log.info(
            "[pregame] saved_comment_rows=%d formatted_notes_chars=%d opponent=%r race=%s",
            len(brief.player_comments),
            len(raw_notes_text),
            brief.opponent_display_name,
            brief.opponent_race,
        )
        if raw_notes_text:
            if brief.inline_saved_notes_in_last_meeting:
                deferred_notes_text = format_expert_notes_for_last_meeting_prompt(
                    brief.opponent_display_name, raw_notes_text
                )
            else:
                msgToChannel(
                    bot,
                    format_saved_notes_for_direct_chat(
                        brief.opponent_display_name, raw_notes_text
                    ),
                    logger,
                )
    else:
        log.info(
            "[pregame] saved_comment_rows=0 opponent=%r race=%s",
            brief.opponent_display_name,
            brief.opponent_race,
        )

    has_saved_notes = bool(raw_notes_text)

    analysis_data: Optional[Dict[str, Any]] = None
    analyzer = None
    ml_supersedes_build_intel = False
    ml_fold_chunks: List[str] = []
    bundle_ml_into_prompt = bool(brief.inline_saved_notes_in_last_meeting and has_saved_notes)
    try:
        analyzer = get_ml_analyzer()
        if db is not None and brief.random_race_intel:
            multi_race = len(brief.random_race_intel) > 1
            last_ad: Optional[Dict[str, Any]] = None
            max_sim = 0.0
            for race, db_row, _, _ in brief.random_race_intel:
                per = analyzer.analyze_opponent_for_chat(
                    brief.opponent_display_name,
                    race,
                    log,
                    db,
                    db_row,
                    prefer_learning_data=False,
                )
                if not per:
                    continue
                last_ad = per
                if _analysis_supersedes_db_build_extract(per):
                    ml_supersedes_build_intel = True
                pt = per.get("analysis_type")
                if pt == "pattern_matching":
                    max_sim = max(
                        max_sim,
                        max(
                            (
                                float(p.get("similarity", 0))
                                for p in (per.get("matched_patterns") or [])
                            ),
                            default=0.0,
                        ),
                    )
                elif pt == "learning_data":
                    max_sim = max(max_sim, 1.0)
                try:
                    pr = f"[As {race}] " if multi_race else ""
                    if bundle_ml_into_prompt:
                        txt = analyzer._format_ml_chat_message(per)
                        if txt:
                            ml_fold_chunks.append(pr + txt)
                            ml_analysis_ran = True
                    elif analyzer.generate_ml_analysis_message(
                        per, bot, log, context_history, prefix=pr
                    ):
                        ml_analysis_ran = True
                except Exception as gen_ex:
                    log.error("Error emitting per-race ML analysis: %s", gen_ex)
            analysis_data = last_ad
            atype = (analysis_data or {}).get("analysis_type")
            log.info(
                "[pregame] pattern_ml_check opponent=%r random_multi=%s type=%s max_pattern_similarity=%.3f "
                "supersedes_db_build=%s",
                brief.opponent_display_name,
                multi_race,
                atype,
                max_sim,
                ml_supersedes_build_intel,
            )
        elif db is not None:
            analysis_data = analyzer.analyze_opponent_for_chat(
                brief.opponent_display_name,
                brief.opponent_race,
                log,
                db,
                None,
                prefer_learning_data=True,
            )
            atype = (analysis_data or {}).get("analysis_type")
            max_sim = 0.0
            if analysis_data and atype == "pattern_matching":
                max_sim = max(
                    (float(p.get("similarity", 0)) for p in (analysis_data.get("matched_patterns") or [])),
                    default=0.0,
                )
            elif analysis_data and atype == "learning_data":
                max_sim = 1.0
            log.info(
                "[pregame] pattern_ml_check opponent=%r type=%s max_pattern_similarity=%.3f "
                "supersedes_db_build=%s",
                brief.opponent_display_name,
                atype,
                max_sim,
                _analysis_supersedes_db_build_extract(analysis_data),
            )
            ml_supersedes_build_intel = _analysis_supersedes_db_build_extract(analysis_data)
            if bundle_ml_into_prompt and analysis_data:
                txt = analyzer._format_ml_chat_message(analysis_data)
                if txt:
                    ml_fold_chunks.append(txt)
                    ml_analysis_ran = True
    except Exception as e:
        log.warning("Pregame pattern/ML check failed: %s", e)
        analysis_data = None
        ml_supersedes_build_intel = False

    extra_ml_context = "\n\n".join(ml_fold_chunks) if ml_fold_chunks else ""

    if (
        not has_saved_notes
        and analysis_data
        and analyzer is not None
        and not brief.random_race_intel
    ):
        try:
            ml_analysis_ran = bool(
                analyzer.generate_ml_analysis_message(
                    analysis_data, bot, log, context_history
                )
            )
        except Exception as e:
            log.error("Error emitting ML opponent analysis: %s", e)

    build_blocks: List[str] = []
    if brief.random_race_intel:
        for race, _, _, steps in brief.random_race_intel:
            if steps:
                build_blocks.append(
                    f"=== Opponent opening as {race} (archived — they are Random today) ===\n"
                    + compose_build_order_user_message(brief.opponent_display_name, steps)
                )
    elif brief.first_few_build_steps:
        build_blocks.append(
            compose_build_order_user_message(
                brief.opponent_display_name, brief.first_few_build_steps
            )
        )

    use_det_opening = (
        bool(getattr(config, "PREGAME_APPEND_DETERMINISTIC_OPENING", True))
        and not has_saved_notes
        and not ml_supersedes_build_intel
        and bool(build_blocks)
    )
    brief.suppress_opponent_training_narrative = use_det_opening

    lm = compose_last_meeting_user_message(
        brief,
        bundled_saved_notes=bool(deferred_notes_text),
        saved_notes_text=deferred_notes_text,
    )
    if deferred_notes_text:
        lm = f"{deferred_notes_text}\n\n" + lm
    if extra_ml_context:
        lm += (
            "\n\n=== Pattern labels (≥85% match — quote quoted strings exactly if you cite them; opponent only) ===\n"
            + extra_ml_context
        )
    hints = brief.opponent_lookup_hints if brief.opponent_lookup_hints else (
        brief.opponent_display_name,
    )
    opener_lines: List[str] = []
    tid: Optional[str] = None
    if db is not None:
        try:
            from core.pregame_matchup_blurb import build_streamer_vs_opponent_tidbit

            tid = build_streamer_vs_opponent_tidbit(
                db, brief.opponent_display_name, hints, logger=log
            )
            if tid:
                opener_lines.append(tid.strip())
        except Exception as e:
            log.debug("matchup tidbit skipped: %s", e)

    rl = (
        format_record_line(brief.record_vs, brief.opponent_display_name)
        if brief.record_vs is not None
        else None
    )
    # Tidbit already states H2H (FSL or replay); do not add a second record line with a different source.
    if rl and not tid:
        rs = rl.strip()
        if rs.lower() not in {x.lower() for x in opener_lines}:
            opener_lines.append(rs)

    had_matchup_openers = bool(opener_lines)
    if opener_lines:
        profile_key = (
            f"{brief.opponent_display_name}|{brief.how_long_ago}|"
            f"{brief.db_result.get('Map', '')}|{brief.db_result.get('Date_Played', '')}"
        )
        profile_idx = sum(ord(ch) for ch in profile_key) % 3
        order_profiles = (
            "record/tidbit first, then strategy, then last-time facts",
            "strategy first, then last-time facts, then record/tidbit",
            "last-time facts first, then strategy, then record/tidbit",
        )
        lm = (
            "Required opener facts (include each exactly once; order can vary): keep these facts exact, "
            "but you may merge them into concise casual wording with natural connectors "
            "(e.g., 'who', 'which was') when it reduces redundancy.\n"
            f"Order profile for this message: {order_profiles[profile_idx]}.\n"
            + "\n".join(f"- {ln}" for ln in opener_lines)
            + "\n\n"
        ) + lm

    # Inline bundle: optional ML — opponent opening is either verbatim suffix (deterministic) or legacy LLM block.
    if (
        brief.inline_saved_notes_in_last_meeting
        and build_blocks
        and not has_saved_notes
        and not ml_supersedes_build_intel
        and not use_det_opening
    ):
        lm += (
            "\n\n=== Opponent opening (same Twitch message; ONE new sentence after prior sentences) ===\n"
            "Max 18 words per block. Use ONLY the abbreviated comma lists — never paste timestamps, "
            "never list workers step-by-step, never echo 'Time:' lines.\n"
            + "\n\n".join(build_blocks)
        )

    opening_suffix = deterministic_opponent_opening_suffix(brief) if use_det_opening else ""

    processMessageForOpenAI(
        bot,
        lm,
        "last_time_played",
        logger,
        context_history,
        response_suffix=opening_suffix,
    )

    if (
        build_blocks
        and not ml_analysis_ran
        and not brief.inline_saved_notes_in_last_meeting
        and not has_saved_notes
        and not ml_supersedes_build_intel
        and not use_det_opening
    ):
        for block in build_blocks:
            processMessageForOpenAI(bot, block, "last_time_played", logger, context_history)
    elif not build_blocks:
        if quiet_when_no_build_extract:
            pass
        elif not getattr(config, "PREGAME_SEND_SEPARATE_GLHF_LINE", False):
            pass
        elif brief.streamer_current_race == "Random":
            msg = (
                f"restate this:  good luck playing {brief.opponent_display_name} in this "
                f"{brief.streamer_current_race} versus {brief.opponent_race} matchup.  Random is tricky."
            )
            processMessageForOpenAI(bot, msg, "last_time_played", logger, context_history)
        else:
            glhf_phrase = getattr(config, "PREGAME_GLHF_PHRASE", "GLHFGG")
            msgToChannel(
                bot,
                f"{glhf_phrase} vs {brief.opponent_display_name} ({brief.opponent_race}).",
                logger,
            )

    line = (
        format_record_line(brief.record_vs, brief.opponent_display_name)
        if brief.record_vs is not None
        else None
    )
    if line and not had_matchup_openers:
        msgToChannel(bot, line, logger)
    elif not line:
        log.debug("[RECORD] Skipping record line (threshold or no parsed head-to-head)")
