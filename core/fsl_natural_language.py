"""
@-mention → LLM chooses an FSL api-server tool → execute allowlisted db.fsl_* → optional LLM formatting.

Not a general chat bot: questions outside FSL league data should return action \"none\".
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Callable, Dict, Optional, Tuple

import settings.config as config
import utils.tokensArray as tokensArray
from core.events import MessageEvent
from core.interfaces import ILanguageModel

logger = logging.getLogger(__name__)


def _extract_json_object(raw: str) -> Optional[Dict[str, Any]]:
    raw = raw.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        return json.loads(m.group())
    except json.JSONDecodeError:
        return None


def _solo_h2h_plan_from_question(question: str) -> Optional[Dict[str, Any]]:
    """
    Solo league head-to-head: patterns like 'when was the last game between A and B'.
    Routes to fsl_matches + Players — never team-league schedule.
    """
    q = question.strip()
    if len(q) < 8:
        return None
    patterns = (
        # "when was the last game between SirMalagant and CrankyToaster"
        r"(?i)when\s+was\s+(?:the\s+)?(?:last|first)\s+(?:game|match|series)\s+between\s+(.+?)\s+and\s+(.+?)(?:\?|\.|!)?\s*$",
        r"(?i)(?:last|first|most\s+recent)\s+(?:game|match|series)\s+between\s+(.+?)\s+and\s+(.+?)(?:\?|\.|!)?\s*$",
        r"(?i)(?:game|match|series)\s+between\s+(.+?)\s+and\s+(.+?)(?:\?|\.|!)?\s*$",
    )
    for pat in patterns:
        m = re.search(pat, q)
        if not m:
            continue
        a, b = m.group(1).strip().strip('"').strip("'"), m.group(2).strip().strip('"').strip("'")
        if not a or not b or len(a) > 120 or len(b) > 120:
            continue
        return {
            "action": "matches",
            "params": {
                "player_name": a,
                "opponent_name": b,
                "season": None,
                "limit": 150,
            },
            "reason": "solo H2H pattern",
        }
    return None


def _solo_division_season_plan_from_question(question: str) -> Optional[Dict[str, Any]]:
    """
    Solo Code S/A/B + season: deterministic route so phrases like 'who won season 1 code A'
    are not misrouted to team_league_season (same words, wrong league).
    """
    q = question.strip()
    if len(q) < 8:
        return None
    if not _question_mentions_solo_code_letter(q):
        return None
    m_season = re.search(r"(?i)\bseason\s*(\d+)", q)
    if m_season:
        season = int(m_season.group(1))
    else:
        m_s = re.search(r"(?i)\bs(\d+)\b", q)
        if not m_s:
            return None
        season = int(m_s.group(1))
    mcode = re.search(r"(?i)\bcode\s*([sab])\b", q)
    if not mcode:
        return None
    letter = mcode.group(1).upper()
    # Solo division snapshot intents (avoid stealing e.g. matches(player) + season questions).
    if not re.search(
        r"(?i)\b("
        r"who\s+won|who\s+was|who\s+is|who\s+came|who\s+got|who\s+finished|"
        r"who\s+(is|was)\s+the\s+(champion|winner)|"
        r"\bchampion\b|\bchamps?\b|"
        r"\bwinner\b|\bwinners\b|"
        r"standings|placement|full\s+standings|table|results|"
        r"second\s+place|\b2nd\b|runner-up|"
        r"leader|ranked|rank\b"
        r")\b",
        q,
    ):
        return None
    return {
        "action": "solo_division_season",
        "params": {"season": season, "division": letter},
        "reason": "solo division code + season pattern",
    }


FSL_API_CHAMPIONSHIP_FIELD_CHEATSHEET = """
--- Canonical DB/API field names for **champion / champ / title** (spot these in routing) ---
• **`Players.Championship_Record`** — official **solo** league titles (Code S/A/B, seasons, etc.). **Champ/champion** about a **player** or **solo division** → this column (+ **`solo_division_season`** surfaces **`official_champion_from_players_record`** when matched).
• **`Players.TeamLeague_Championship_Record`** — **team-league** championship text on the **same player row** (not the same meaning as solo Code S).
• **`Teams.TeamLeague_Championship_Record`** — **team organization** championship / season story. **Which team won** / **team league champion** → **`team_league_season`** and/or **`team_detail`** (this field).

"""


FSL_DATA_MODEL_AND_SCENARIOS = (
    FSL_API_CHAMPIONSHIP_FIELD_CHEATSHEET
    + """
--- What the linked FSL (psistorm) API exposes (read-only) ---
• **Players**: Identity search by Real_Name substring (`players_search`). Exact-name row + joins for tool resolution (`player_detail`). Fields used: Player_ID, Real_Name, Team_ID (link only), Status, Team_Name via join; **`Championship_Record`**, **`TeamLeague_Championship_Record`** when present.

• **Teams** + **Players join**: `teams_search` / `team_detail` (one row from Teams). **Roster** (`team_roster`): all `Real_Name` on that `Team_ID`, with role captain / co_captain / member by matching `Players.Player_ID` to `Teams.Captain_ID` / `Co_Captain_ID`.

• **Team league (schedule)** vs **solo league**: **`fsl_schedule`** = **organizations** (`team1_name` vs `team2_name`, **`winner_team_name`**). **`fsl_matches`** joins **`Players`** (`winner_name`, `loser_name`) — **solo** series between **two player Real_Names**. **Never** use **`schedule`** for "**between [player] and [player]**" / "**when was the … game between …**" — that is **`matches`** (solo), not team calendar.

• **FSL_STATISTICS**: Per Player_ID — Division, Race, MapsW/L, SetsW/L (career aggregates split by division × race). **There is no season column** on these rows in our API → for "record / win% **in season N**", use **`matches`** with `season`, not `player_detail`.

• **fsl_matches**: One row per **solo-league series**. **leaderboard_total_wins** = most **series** won (COUNT as `winner_player_id`). **leaderboard_win_pct** = best series win **%**.
• **FSL_STATISTICS**: **leaderboard_maps_won** = **SUM(MapsW)** per player **after deduping** to one row per Division×Race via **MIN(Alias_ID)** (same as player_statistics) — career **map/game wins** — ties possible; not the same as series count.

• **fsl_schedule**: Team-league calendar rows (scores, winner_team_name). **`GET .../team-league/season/{n}/summary`** = **standings + finals-week winner** for “who won the season / champion”. Use **`schedule`** for **week-by-week listing** only.

• **Solo league divisions (Code S / A / B)**: **`fsl_matches.t_code`** ('S','A','B'). **Official division champion/title** for a season is recorded in **`Players.Championship_Record`** (surfaced on **`solo_division_season`** as **official_champion_from_players_record** when the API finds a matching row). **Standings** in that endpoint are **series W-L from matches** — use for records/placement; **“the champion”** in the league-title sense → **Championship_Record**, not standings alone. **champ** = **champion**. **Not** **`team_league_season`** (team orgs).

--- Typical viewer intent → pick ONE action ---
• "Who is … / find player / spelling" → `players_search`
• "Stats / maps & sets / races & divisions / overall FSL numbers for a player" (career, from FSL_STATISTICS) → `player_detail` (also shows **Championship_Record** / **TeamLeague_Championship_Record** from Players when API returns them)
• "**Which team won season N** / **team league champion** / **who won team league** / **season N champion** (team **organization**) → **`team_league_season`** with **`season`** = N — **not** raw **`schedule`** dump (that’s for calendars). **Not** **`leaderboard_*`** (solo careers).
• "**Code S / Code A / Code B** / **solo division** / **placement** / **who came 2nd** / **who won [season] code X** / **winner of code X season N** as a **player** in a division + season → **`solo_division_season`** with **`season`** + **`division`** (e.g. `"Code S"` or `"S"`). **Never** **`team_league_season`** for **player** / **Code S** wording — that action is **team league only**.
• "**List teams** / **teams in FSL** / **all teams** → **`teams_search`** with **empty `q`** (lists teams).
• "**Players on team X** / **in team X** / **roster** / **members of [team]** → **`team_roster`** with **`name`** = team phrase — **not** `players_search` (that matches **player Real_Name** substrings only).
• "Team … / org / **TeamLeague_Championship_Record** string" → `team_detail`; **roster / team members / who plays for** → `team_roster`; browse names → `teams_search`
• "**When was / last game / head-to-head between PLAYER_A and PLAYER_B** (two solo names) → **`matches`** with **`player_name`** + **`opponent_name`** — **`fsl_matches`** + **`Players`**. **Not** **`schedule`** (teams).
• "When does **team** X play / **team league** schedule / week N / season S **team** games" → `schedule`
• "Last games / results / vs everyone / record **in a season** (one player)" → `matches` with player_name (+ season when asked)
• "**Overall / career record** / **how many times** / **win %** between two solo players → **`matches_h2h`** (`player_name`, `opponent_name`, optional **`season`**) — **full aggregate** API, not a truncated list.
• "**A vs B** / **last games** / **list matches** / **head to head** (want **rows**) → `matches` with player_name + opponent_name (+ optional season)
• "Best **win %** / winrate percentage" → `leaderboard_win_pct`
• "Most **map** wins / **game** wins / total maps / FSL_STATISTICS career maps" → **`leaderboard_maps_won`** (ties at same deduped total possible — list top N).
• "Most **series** won / most matchups / BoX wins (one row per series in `fsl_matches`)" → `leaderboard_total_wins`
• "Match **by id** / fsl_match_id / game number …" (numeric id) → `match_detail`
• Prefer `player_detail` by name over `statistics_player`; use `statistics_player` only when they give a numeric Player_ID.

--- Use action `none` when ---
• Replay archive / Mathison DB / ladder / non-FSL topics.
• Season-specific **division×race map totals** if those only exist in FSL_STATISTICS (no season column there) — **none** unless **`matches`** can answer; **solo division placement / Code S standings** → **`solo_division_season`**, not none.
• Needs data outside these tables or vague with no entity to search.
"""
)


# Compact surface for stage-1 “which API/domain?” — prefer editing this + SCHEMA_GROUNDING_PROMPT_TEMPLATE
# over piling rules into _ROUTER_CRITICAL when FSL_ASK_SCHEMA_GROUNDING is True.
FSL_API_SCHEMA_GROUNDING = (
    """
Championship / title columns (exact names — map viewer **champ**/**champion** to these):
**`Players.Championship_Record`** (solo division titles); **`Players.TeamLeague_Championship_Record`** (player’s team-league text); **`Teams.TeamLeague_Championship_Record`** (team org).

Available read-only surfaces (conceptual → bot picks one JSON action):

1) **Solo league series — `fsl_matches`**  
   Each row is one BoX series; joins **Players** for winner/loser **Real_Name**; **`t_code`** = division letter **S/A/B** (Code S/A/B — **same meaning** whether viewers type **code s** or **Code S**). Treat **champ** as **champion**.  
   Use for: one player’s series history; **head-to-head between two player names**; “last game between A and B”; season-specific solo record; **`GET .../solo-league/season/{n}/division/{S|A|B}/standings`** for **division standings / who placed 2nd in Code S** in a season.  
   **`GET .../matches/h2h`** = **full** career (or season) **totals** + naive win-% from series history — use for “overall record”, “how many times”, “career H2H”. **`GET .../matches`** = **list** of recent rows (limited).  
   **Not** for team-org vs team-org calendar.

2) **Team league — `fsl_schedule` + season summary API**  
   **`fsl_schedule`** = week-by-week match rows. **`GET .../team-league/season/{n}/summary`** = **standings** + **winner of highest week** (proxy for finals / season champion). Use **summary** for “who won season N / champion”; use **schedule** for calendar listing.  
   **Not** for two **solo player** nicknames’ head-to-head (`fsl_matches`).

3) **Career aggregates — `FSL_STATISTICS`**  
   Per player, division×race maps/sets; map-win **leaderboard** uses deduped rows. No season column.

4) **Identity / org browse**  
   **Players** search; **Teams** search + **team roster** (players on a team by team name).

5) **Solo career leaderboards** (derived from `fsl_matches` or `FSL_STATISTICS`)  
   Series wins, win %, map wins — not team-season champions.
"""
)


FSL_CHAT_DOMAIN_PREAMBLE = """DOMAIN — almost every message is **FSL league data** (PSISTORM / StarCraft II): Twitch chat about **teams**, **players**, **solo vs team league**, **seasons/weeks**, **statistics**, **standings**, **records**, **maps**, **BoX series**, **head-to-head**, **winner/champion/champ**, **placement**, **Code S/A/B**. Title columns: **`Championship_Record`** (solo, on **Players**), **`TeamLeague_Championship_Record`** on **Players** vs **Teams**. **champ = champion**, informal casing (**code s** = **Code S**) — infer league intent unless the QUESTION clearly isn’t FSL data."""


SCHEMA_GROUNDING_PROMPT_TEMPLATE = """You map a Twitch viewer question to the correct FSL league API **domain** (not JSON yet).

""" + FSL_CHAT_DOMAIN_PREAMBLE + """

Here is what exists (do not invent tables or endpoints):
""" + FSL_API_SCHEMA_GROUNDING + """
Instructions:
- Reply in 4–8 short sentences: which numbered domain(s) apply, and **explicitly** what to avoid if wording is ambiguous (e.g. “two player names → solo fsl_matches H2H, not team schedule”).
- Do **not** output JSON, SQL, or made-up API paths.
- If the question is not answerable from these surfaces, say so in one sentence.

QUESTION:
"{question}"
"""


_ROUTER_CRITICAL = """
CRITICAL routing (misrouting changes numbers — never mix these up):
- **Champion/champ/title field names:** **`Players.Championship_Record`** = solo official titles (Code S player questions). **`Teams.TeamLeague_Championship_Record`** = **team org** story (team league champion). **`Players.TeamLeague_Championship_Record`** = player’s **team-league** text — do not confuse with solo **`Championship_Record`**.
- **Two solo player names** / **between X and Y** / **when was the … game between …** / **last match between …** → **`matches`** with **`player_name`** + **`opponent_name`** (**`fsl_matches`**). **Never** **`schedule`** — **`schedule`** is **team-vs-team** rows, **not** two **`Players`** from **`fsl_matches`**.
- **Team league champion** / **which team won season N** / **team org** sense → **`team_league_season`** with **`season`**. **Never** dump **`schedule`** alone for “champion” — use the **summary** action.
- **Who won / winner / who is the winner** when the question also says **Code S / Code A / Code B** (solo division letter) → **`solo_division_season`**, **not** **`team_league_season`**. Viewers mean the **solo division** title/standings, not team organizations.
- **Code S / Code A / Code B** (any casing: code s, CODE S) / **solo division** / **player placement** / **2nd place player** in a division + season → **`solo_division_season`** (`season`, `division`). **Colloquial "champ" = champion** (same intent). **Never** **`team_league_season`** — that is **team league schedule standings**, not **`fsl_matches.t_code`** solo divisions.
- Generic **team league** questions that need **calendar games** / **week** → **`schedule`**. **Never** **`leaderboard_total_wins`**, **`leaderboard_maps_won`**, or **`leaderboard_win_pct`** for team-season champion — those are **solo-player** career stats.
- Phrases **players on/in/for team …** / **roster** / **members of [team name]** → **`team_roster`** with **`name`** = the team wording. **Never** **`players_search`** — it searches **player nicknames**, not organization membership.
- Words **map / maps / map wins / maps won / total maps / game wins** meaning **individual games (maps)** → **`leaderboard_maps_won`** ONLY. **Never** **`leaderboard_total_wins`** for that — that counts **solo series** wins from `fsl_matches` (often ~54), not ~127 map wins from `FSL_STATISTICS`.
- Words **series / BoX / matchups / series wins** about **solo career** leaders → **`leaderboard_total_wins`**.
- If both map and series **leaderboard** meaning could apply (solo careers), **map wording wins** → **`leaderboard_maps_won`**.
"""


ROUTER_PROMPT_TEMPLATE = """You route Twitch viewer questions to the FSL (psiStorm league) DATABASE tools only.

""" + FSL_CHAT_DOMAIN_PREAMBLE + """
You must respond with a single JSON object and nothing else (no markdown fence).
""" + _ROUTER_CRITICAL + """
QUESTION (after removing the bot mention):
"{question}"

{schema_grounding_block}
""" + FSL_DATA_MODEL_AND_SCENARIOS + """
ALLOWED action values:
- "none" — Not about FSL league data we store (general SC2 strategy, replay/archive DB, jokes, real life, unclear), OR needs data we cannot query.
- "players_search" — Find players by name substring. params: {{"q": "<text>", "limit": <1-12 optional>}}
- "player_detail" — One player's FSL stats rows (division/race maps/sets). params: {{"name": "<player name>"}}
- "teams_search" — Find teams by substring; **`q` empty or omitted** = list teams (alphabetical). params: {{"q": "<text or empty>", "limit": <optional>}}
- "team_detail" — One team's row (championship record string, status). params: {{"name": "<team name>"}}
- "team_roster" — **Player names on that team** (join Players on Team_ID; captain/co from Teams). params: {{"name": "<team name substring>"}}
- "team_league_season" — **Team league** (organizations) **season champion / standings** from **`fsl_schedule`**. params: {{"season": <int>}}
- "solo_division_season" — **Solo league** **Code S/A/B** **standings for one season** from **`fsl_matches.t_code`** (series W-L). params: {{"season": <int>, "division": "<Code S | Code A | Code B | S | A | B>"}}
- "schedule" — Team league **calendar** rows (list games). params: {{"season": <int or null>, "week": <int or null>, "limit": <5-20 optional>}}
- "matches_h2h" — **Career** (or one season) **totals** between two players: series W-L, maps sums, naive next-series % from history. params: {{"player_name":"<text>","opponent_name":"<text>","season":<int or null>}}
- "matches" — Solo league (`fsl_matches`) **row list** (limited).
  • One player: params {{"player_name":"<text>","season":<int or null>,"limit":<optional>}}
  • One player **in a season** ("record in season 10", "how did X do in S9"): same — **matches** with **player_name** + **season** (answers from series W/L in that season).
  • **Head-to-head list (two players)**: params {{"player_name":"<first>","opponent_name":"<second>","season":<int or null>}} — recent series rows between those two names.
- "leaderboard_win_pct" — Best **win percentage** (series). params: {{"min_matches":<int optional default 10>, "limit":<optional>}}
- "leaderboard_total_wins" — Most **series** won (`fsl_matches` winner count). params: {{"min_matches":<int optional default 1>, "limit":<optional>}}
- "leaderboard_maps_won" — Most career **map wins** (`FSL_STATISTICS`: one row per Division×Race via `MIN(Alias_ID)`, then sum `MapsW` per player). params: {{"limit":<optional>}}
- "match_detail" — One match by id. params: {{"match_id": <int>}}
- "statistics_player" — Same aggregate rows as player_detail but by numeric id only. Prefer "player_detail" with name for names. params: {{"player_id": <int>}}

Guidance:
- Before choosing: read **FSL_DATA_MODEL_AND_SCENARIOS** above — match intent to table strengths (especially: season-specific → `matches`; career div/race totals → `player_detail`).
- If they ask "who is", "find", "search" + player → players_search (unless they want full stats → player_detail).
- **"when"** + **two player-style names** + **between … and …** → **`matches`** H2H, **not** schedule. **`schedule`** only when the question is **team-league calendar** (team org names, week, when a **team org** plays, etc.).
- "**Career / overall** H2H, **how many times** played, **total** record → **`matches_h2h`**. **List of games** / **last meeting** → **`matches`** with both names.
- Questions like "X's record vs Y" **totals** → **`matches_h2h`**; **recent / list** → **matches** with **both** player_name and opponent_name.
- "**Win percentage**" → **leaderboard_win_pct**. "**Games/maps won** (same thing here)" → **leaderboard_maps_won**. "**Series** won (matchups)" → **leaderboard_total_wins**. Do not use series leaderboard for a pure map/game count question.
- "**Which team won season N** / **team league champion** (team **org**) → **`team_league_season`** (`season`). **Who won season N Code S/A/B** / **winner … code a** → **`solo_division_season`** (`season`, `division`). **Code S / solo division placement** → **`solo_division_season`** (`season`, `division`). **Calendar week listing** → **`schedule`**. **Team members / roster …** → **team_roster**, not **players_search** or team_detail alone.
- Extract integers for season/week/match_id from phrases like "season 9", "s9", "week 3".
- When unsure, prefer "none".

Return exactly:
{{"action":"<one of the above>","params":{{...}},"reason":"<10 words max>"}}
"""


# Second LLM often hallucinates counts on leaderboards — bypass it for these actions by default.
_DEFAULT_SKIP_FORMAT_ACTIONS = frozenset({
    "leaderboard_win_pct",
    "leaderboard_total_wins",
    "leaderboard_maps_won",
    "teams_search",
    "team_detail",
    "team_roster",
    "schedule",
    "matches",
    "matches_h2h",
})


def _pick_row_field(row: Dict[str, Any], *keys: str) -> Any:
    """PHP/MySQL JSON keys may vary in case; normalize."""
    if not row:
        return None
    lower = {str(k).lower(): v for k, v in row.items()}
    for k in keys:
        if k.lower() in lower:
            return lower[k.lower()]
    return None


def _normalize_solo_division_t_code(raw: Optional[Any]) -> Optional[str]:
    """Map viewer/router phrasing → fsl_matches.t_code letter S, A, or B."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    u = s.upper()
    if len(u) == 1 and u in ("S", "A", "B"):
        return u
    if re.search(r"(?i)\bCODE\s*S\b", s):
        return "S"
    if re.search(r"(?i)\bCODE\s*A\b", s):
        return "A"
    if re.search(r"(?i)\bCODE\s*B\b", s):
        return "B"
    return None


_FIRST_PLACE_MARKER = "mean THIS line (not missing data):"
_OFFICIAL_CHAMP_MARKER = (
    "Official champion for this division/season (Players.Championship_Record):"
)


def _parse_solo_season_label(facts: str) -> Tuple[Optional[str], str]:
    """Season number and division label from solo division FACTS."""
    m = re.search(r"Season\s+(\d+)\s+solo league\s+(Code\s+[SAB])\b", facts, re.I)
    if m:
        return m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
    m2 = re.search(r"Season\s+(\d+)\s+solo league\s+t_code\s+([SAB])\b", facts, re.I)
    if m2:
        return m2.group(1), f"Code {m2.group(2).upper()}"
    return None, "Code S"


def _parse_solo_division_first_place(
    facts: str,
) -> Optional[Tuple[Tuple[str, ...], Optional[Tuple[int, int]], bool]]:
    """Parse rank-1 names, optional W-L, tie-at-top from FACTS."""
    if _FIRST_PLACE_MARKER not in facts:
        return None
    idx = facts.index(_FIRST_PLACE_MARKER) + len(_FIRST_PLACE_MARKER)
    rest = facts[idx:].lstrip()
    line = rest.split("\n")[0].strip().rstrip(".")
    tied = "(tied at top)" in line.lower()
    line = re.sub(r"\s*\(tied at top\)\.?\s*$", "", line, flags=re.I).strip()
    wm = re.search(r"^(.+?)\s*\((\d+)-(\d+)\)\s*$", line)
    if wm:
        names_blob = wm.group(1).strip()
        wl = (int(wm.group(2)), int(wm.group(3)))
    else:
        names_blob = line.rstrip(".").strip()
        wl = None
    names = tuple(x.strip() for x in names_blob.split(",") if x.strip())
    if not names:
        return None
    return names, wl, tied


def _question_mentions_solo_code_letter(question: str) -> bool:
    """Detects Code S/A/B wording in viewer text — case-insensitive (`Code S` vs `code s`)."""
    return bool(re.search(r"(?i)\bcode\s*[sab]\b", question))


def _question_asks_solo_champion_not_second(question: str) -> bool:
    """True when the viewer asks who won/champion/first — not a 2nd-place-only question."""
    q = question.lower()
    # champ / champs / champion / champions — also teach router/format LLM: champ = champion
    champ_q = r"\bchampion(?:s)?\b|\bchamps?\b"
    asks_second_only = bool(
        re.search(r"\b2nd\b|second\s+place|runner-up", q)
        and not re.search(rf"{champ_q}|\bwho\s+won\b|first\s+place", q)
    )
    if asks_second_only:
        return False
    if re.search(champ_q, q):
        return True
    if re.search(r"\bwho\s+won\b", q):
        return True
    if re.search(r"\b(first\s+place|won\s+(?:the\s+)?division|division\s+winner)\b", q):
        return True
    if re.search(r"\bwho\s+(was|is)\s+the\s+winner\b", q):
        return True
    if _question_mentions_solo_code_letter(question) and re.search(
        r"\b(winner|winners)\b", q
    ):
        return True
    if re.search(r"\bfirst\s+place\b", q):
        return True
    if re.search(r"\bwho\s+(was|is)\b", q) and _question_mentions_solo_code_letter(question):
        return True
    return False


def _parse_official_champion_name(facts: str) -> Optional[str]:
    """Players.Championship_Record line → single official name (preferred over standings)."""
    if _OFFICIAL_CHAMP_MARKER not in facts:
        return None
    rest = facts[facts.index(_OFFICIAL_CHAMP_MARKER) + len(_OFFICIAL_CHAMP_MARKER) :].strip()
    line = rest.split("\n")[0]
    m = re.match(r"^(.+?)\s*\[player_id", line)
    if not m:
        return None
    return m.group(1).strip()


def _draft_solo_division_champion_reply(facts: str, question: str) -> Optional[str]:
    """Stable reply for champ/champion questions — ONLY Players.Championship_Record (never standings W/L)."""
    if not _question_asks_solo_champion_not_second(question):
        return None
    official = _parse_official_champion_name(facts)
    season, label = _parse_solo_season_label(facts)
    season_s = season or "?"
    if official:
        return (
            f"{official} was the {label} champion for season {season_s} "
            f"(official: Players.Championship_Record)."
        )[:450]
    # Do not infer "champion" from fsl_matches standings — that lists series W-L only.
    return (
        f"No matching row in Players.Championship_Record for {label} season {season_s} "
        f"(solo official title). "
        f"Standings below are series W-L only - not used to name champion."
    )[:450]


def _fmt_players(data: Dict[str, Any]) -> str:
    rows = data.get("players") or []
    if not rows:
        return "No players found."
    bits = []
    for r in rows[:10]:
        nm = r.get("Real_Name") or "?"
        tid = r.get("Team_Name") or ""
        bits.append(f"{nm} (id {r.get('Player_ID')})" + (f" [{tid}]" if tid else ""))
    return "FSL players: " + " | ".join(bits)


def _fmt_teams(data: Dict[str, Any]) -> str:
    rows = data.get("teams") or []
    if not rows:
        return "No teams found."
    shown = rows[:40]
    bits = [
        f"{r.get('Team_Name')} (id {r.get('Team_ID')}, {r.get('Status')})" for r in shown
    ]
    if len(rows) > len(shown):
        head = f"FSL teams ({len(rows)}, showing {len(shown)}): "
        tail = f" … (+{len(rows) - len(shown)} more)"
    else:
        head = "FSL teams: "
        tail = ""
    return head + " | ".join(bits) + tail


def _fmt_team_detail(row: Dict[str, Any]) -> str:
    nm = row.get("Team_Name") or "?"
    tid = row.get("Team_ID")
    tl = row.get("TeamLeague_Championship_Record") or ""
    cap = row.get("Captain_ID")
    co = row.get("Co_Captain_ID")
    st = row.get("Status") or ""
    lines = [f"FSL team {nm} (id {tid}), status {st}."]
    if tl:
        lines.append(f"Team league championship record (Teams DB string): {tl}")
    lines.append(
        f"Captain / co-captain player ids: {cap}, {co}. "
        f"Ask roster for Real_Name lines."
    )
    return "\n".join(lines)


def _fmt_team_roster(team_row: Dict[str, Any], payload: Dict[str, Any]) -> str:
    tname = team_row.get("Team_Name") or "?"
    tid = team_row.get("Team_ID")
    if payload.get("_roster_endpoint_unavailable"):
        cap = team_row.get("Captain_ID")
        co = team_row.get("Co_Captain_ID")
        return (
            f"Roster names need api-server route GET /api/v1/fsl/teams/{{id}}/players (currently 404 on server). "
            f"Deploy latest FslDatabase + fsl.php. Until then — team {tname!r} (id {tid}): "
            f"captain player_id={cap}, co-captain player_id={co}."
        )
    rows = payload.get("players") or []
    if not rows:
        return f"No Players rows with Team_ID={tid} for team {tname!r}."
    lines = [
        f"FSL team {tname} (id {tid}) roster — solo league Players table (captain/co from Teams match):"
    ]
    for r in rows[:40]:
        role = (r.get("roster_role") or "member").replace("_", " ")
        nm = r.get("Real_Name") or "?"
        pid = r.get("Player_ID")
        st = r.get("Status") or ""
        lines.append(f"  {nm} — {role}" + (f", status {st}" if st else "") + f" [player_id {pid}]")
    return "\n".join(lines)


def _fmt_team_league_season(data: Dict[str, Any]) -> str:
    """Facts for team league season — structured for an LLM to answer champion / placement questions."""
    if data.get("_team_league_summary_unavailable"):
        return (
            "Team league season summary needs GET /api/v1/fsl/team-league/season/{n}/summary "
            "(deploy api-server FslDatabase::teamLeagueSeasonSummary + fsl.php)."
        )
    s = data.get("summary") or {}
    if s.get("note") and not s.get("schedule_rows"):
        return f"Team league season {s.get('season')}: {s.get('note')}"
    season = s.get("season")
    champ = s.get("champion_from_final_week_match")
    tie = s.get("standings_tie_at_top")
    standings = s.get("standings") or []
    lines = [
        f"Season {season} team league (from fsl_schedule aggregates).",
        (
            f"Finals-week proxy (winner of highest week_number): {champ or '?'} "
            f"(week {s.get('last_week_number')})."
        ),
    ]
    if standings:
        ranked = []
        for i, r in enumerate(standings[:12], start=1):
            nm = r.get("team_name") or "?"
            w, l = r.get("wins", 0), r.get("losses", 0)
            ranked.append(f"{i}) {nm} {w}-{l}")
        lines.append(
            "Standings rank (1 = best record by API sort: wins desc, losses asc): "
            + " ; ".join(ranked)
        )
        if len(standings) >= 2:
            second = standings[1]
            lines.append(
                f"Second place team (row 2 in that rank order): {second.get('team_name') or '?'} "
                f"({second.get('wins', 0)}-{second.get('losses', 0)})."
            )
        if tie:
            lines.append("There is a tie at the top of the standings (see row 1).")
    lines.append(
        "Official stored title string may also appear on Teams.TeamLeague_Championship_Record (team_detail)."
    )
    return "\n".join(lines)


def _fmt_solo_division_season(data: Dict[str, Any]) -> str:
    """Facts for solo Code S/A/B season standings — LLM answers placement questions."""
    if data.get("_solo_division_standings_unavailable"):
        return (
            "Solo division season standings need GET "
            "/api/v1/fsl/solo-league/season/{n}/division/{S|A|B}/standings "
            "(deploy api-server FslDatabase::soloDivisionSeasonStandings + fsl.php)."
        )
    s = data.get("summary") or {}
    if not s and not data.get("_solo_division_standings_unavailable"):
        return "Solo division season summary was empty (check API / database client)."
    if s.get("error"):
        return f"Solo division standings: {s.get('error')}"
    season = s.get("season")
    label = s.get("division_label") or ""
    tc = s.get("division_t_code") or ""
    n_matches = int(s.get("match_row_count") or 0)
    standings = s.get("standings") or []
    second_names = s.get("second_place_player_names") or []
    lines = [
        f"Season {season} solo league {label or ('t_code ' + str(tc))} "
        f"(series W-L from fsl_matches rows with this season and t_code; {n_matches} match rows).",
    ]
    oc = s.get("official_champion_from_players_record")
    has_official = isinstance(oc, dict) and bool(oc.get("player_name"))
    if not has_official:
        lines.append(
            "**Official solo champion** comes from **`Players.Championship_Record`** only. "
            "This API call did **not** match stored text for that title — "
            "standings below are **schedule/series record**, not definitive champion title."
        )
    if has_official:
        pid = oc.get("player_id")
        cr = oc.get("championship_record")
        excerpt = ""
        if cr is not None:
            excerpt = str(cr).replace("\n", " ").strip()
            if len(excerpt) > 240:
                excerpt = excerpt[:237] + "..."
        lines.append(
            f"{_OFFICIAL_CHAMP_MARKER} {oc.get('player_name')} [player_id {pid}]."
            + (f" Raw field: {excerpt}" if excerpt else "")
        )
    first_names: list[str] = []
    if standings:
        for row in standings:
            try:
                rnk = int(row.get("rank") or 0)
            except (TypeError, ValueError):
                rnk = 0
            if rnk == 1:
                nm = row.get("player_name") or "?"
                if nm not in first_names:
                    first_names.append(nm)
    if standings:
        ranked = []
        for row in standings[:16]:
            rnk = row.get("rank")
            nm = row.get("player_name") or "?"
            w, l = row.get("wins", 0), row.get("losses", 0)
            mm = row.get("map_margin")
            mm_bit = f" map_margin={mm}" if mm is not None else ""
            ranked.append(f"{rnk}) {nm} {w}-{l}{mm_bit}")
        lines.append(
            "Standings rank (series W-L; identical W-L breaks by map_margin sum, then H2H among tied): "
            + " ; ".join(ranked)
        )
    if first_names:
        r1 = next(
            (
                x
                for x in standings
                if int(x.get("rank") or 0) == 1
            ),
            None,
        )
        wl = ""
        if r1 is not None:
            wl = f" ({r1.get('wins', 0)}-{r1.get('losses', 0)})"
        tie_top = len(first_names) > 1
        cap = (
            "Standings best series record (fsl_matches), rank 1 — for **schedule W-L** questions only. "
            if has_official
            else (
                "Standings leader by series W-L (fsl_matches), rank 1 — "
                "**not** synonymous with **`Players.Championship_Record`** champion title: "
            )
        )
        if has_official:
            lines.append(
                cap
                + ", ".join(first_names)
                + wl
                + (" (tied on record)." if tie_top else ".")
                + " For **official division champion/title**, use Players.Championship_Record line above."
            )
        else:
            lines.append(
                cap
                + ", ".join(first_names)
                + wl
                + (" (tied on record)." if tie_top else ".")
            )
    if second_names:
        lines.append(
            "Second place player(s) (rank 2): " + ", ".join(second_names) + "."
        )
    elif standings:
        lines.append(
            "Second place player(s): none computed (fewer than 2 players in standings or rank-2 empty)."
        )
    if not standings and n_matches == 0:
        lines.append(
            "No fsl_matches rows for this season and division t_code — cannot build standings."
        )
    note = s.get("interpretation_note")
    if note:
        lines.append(str(note))
    return "\n".join(lines)


def _fmt_schedule(data: Dict[str, Any]) -> str:
    rows = data.get("schedule") or []
    if not rows:
        return "No schedule rows."
    lines = []
    seasons = {s.get("season") for s in rows[:50] if s.get("season") is not None}
    if len(seasons) == 1:
        lines.append(
            f"Team-league schedule (season {next(iter(seasons))}; winner_team_name per row when present):"
        )
    else:
        lines.append("Team-league schedule (winner_team_name per row when present):")
    for s in rows[:12]:
        w = s.get("winner_team_name") or "?"
        lines.append(
            f"S{s.get('season')} W{s.get('week_number')}: "
            f"{s.get('team1_name')} vs {s.get('team2_name')} "
            f"{s.get('team1_score')}-{s.get('team2_score')} "
            f"winner={w} ({s.get('match_date')})"
        )
    return "\n".join(lines)


def _fmt_matches(
    data: Dict[str, Any],
    *,
    player_name: Optional[str] = None,
    opponent_name: Optional[str] = None,
    season: Optional[int] = None,
) -> str:
    rows = data.get("matches") or []
    if not rows:
        return "No matches found."
    lines = []
    if player_name and opponent_name:
        from core.handlers.fsl_query_handler import _h2h_series_summary

        lines.append(_h2h_series_summary(rows, player_name, opponent_name))
        latest = rows[0]
        lines.append(
            "Most recent solo-league series in this list (fsl_matches, ordered by match id desc): "
            f"{latest.get('winner_name')} beat {latest.get('loser_name')} "
            f"{latest.get('map_win')}-{latest.get('map_loss')} "
            f"(season {latest.get('season')}, fsl_match_id {latest.get('fsl_match_id')})."
        )
    elif player_name and season is not None:
        from core.handlers.fsl_query_handler import player_series_record_line

        rec = player_series_record_line(rows, player_name, season)
        if rec:
            lines.append(rec)
    for r in rows[:12]:
        lines.append(
            f"{r.get('winner_name')} > {r.get('loser_name')} "
            f"{r.get('map_win')}-{r.get('map_loss')} (s{r.get('season')}, id {r.get('fsl_match_id')})"
        )
    return "FSL matches:\n" + "\n".join(lines)


def _fmt_h2h_summary(data: Dict[str, Any]) -> str:
    """Full career (or season) aggregates from GET /api/v1/fsl/matches/h2h."""
    if data.get("_h2h_endpoint_unavailable"):
        return (
            "Head-to-head summary needs GET /api/v1/fsl/matches/h2h on api-server "
            "(deploy latest FslDatabase.php + fsl.php routes)."
        )
    row = data.get("h2h") or {}
    aq = row.get("player_a_query") or "?"
    bq = row.get("player_b_query") or "?"
    st = row.get("season_filter")
    scope = f"season {st}" if st is not None else "all seasons"
    n = int(row.get("series_total") or 0)
    wa = int(row.get("series_wins_a") or 0)
    wb = int(row.get("series_wins_b") or 0)
    ma = int(row.get("maps_won_a") or 0)
    mb = int(row.get("maps_won_b") or 0)
    lines = [
        f"FSL head-to-head summary ({scope}; solo BoX series in fsl_matches):",
    ]
    if n == 0:
        lines.append(f"No series between {aq!r} and {bq!r} (try alternate spelling).")
        return "\n".join(lines)
    lines.append(f"Series record: {aq} {wa}-{wb} {bq} ({n} series).")
    lines.append(f"Maps won (summed over those series): {aq} {ma}, {bq} {mb}.")
    pa = row.get("next_series_win_prob_a")
    pb = row.get("next_series_win_prob_b")
    try:
        fa = float(pa) if pa is not None else None
        fb = float(pb) if pb is not None else None
    except (TypeError, ValueError):
        fa = fb = None
    if fa is not None and fb is not None and n > 0:
        lines.append(
            "Naive next-series marginal from historical series W/L only "
            f"(Laplace add-one; not skill estimate, not other opponents): "
            f"{aq} ~{fa * 100:.1f}% vs {bq} ~{fb * 100:.1f}%."
        )
        if abs(fa - fb) < 0.02:
            lines.append("Nearly even by this crude historical model.")
        else:
            fav = aq if fa > fb else bq
            pct = max(fa, fb) * 100
            lines.append(
                f"Weak historical lean (for chat flavor only): {fav} ~{pct:.1f}% implied next-series marginal."
            )
    note = row.get("empirical_note")
    if note:
        lines.append(str(note)[:240])
    return "\n".join(lines)


def _fmt_leaderboard_win_pct(data: Dict[str, Any]) -> str:
    rows = data.get("leaderboard") or []
    if not rows:
        return "No leaderboard rows (threshold may be too high or API empty)."
    out = [
        "FSL career match win % (each row = one series in fsl_matches; min games from API):"
    ]
    for r in rows[:20]:
        raw = r.get("win_pct")
        try:
            pct = float(raw)
        except (TypeError, ValueError):
            pct = 0.0
        if pct <= 1.0:
            pct *= 100.0
        nm = r.get("Real_Name") or "?"
        w, l = r.get("wins"), r.get("losses")
        mp = r.get("matches_played")
        out.append(f"  {nm}: {pct:.1f}% ({w}-{l}, n={mp})")
    return "\n".join(out)


def _fmt_leaderboard_total_wins(data: Dict[str, Any]) -> str:
    if data.get("_total_wins_endpoint_unavailable"):
        return (
            "Total-wins leaderboard needs GET /api/v1/fsl/statistics/leaderboard/total-wins "
            "(404 — deploy latest api-server FslDatabase + fsl.php)."
        )
    rows = data.get("leaderboard") or []
    if not rows:
        return "No leaderboard rows (threshold may filter everyone out)."
    out = [
        "FSL career series **wins** (each fsl_matches row = one series won or lost; sorted by wins desc):"
    ]
    for r in rows[:20]:
        nm = r.get("Real_Name") or "?"
        w, l = r.get("wins"), r.get("losses")
        mp = r.get("matches_played")
        out.append(
            f"  {nm}: {w} series wins as winner in fsl_matches ({w}-{l}, n={mp} series)"
        )
    return "\n".join(out)


def _fmt_leaderboard_maps_won(data: Dict[str, Any]) -> str:
    if data.get("_maps_won_endpoint_unavailable"):
        return (
            "Maps-won leaderboard needs GET /api/v1/fsl/statistics/leaderboard/maps-won "
            "(404 — deploy api-server)."
        )
    rows = data.get("leaderboard") or []
    if not rows:
        return "No FSL_STATISTICS rows for maps leaderboard."
    out = [
        "FSL map wins (SUM(MapsW) after dedupe: one row per Player_ID+Division+Race via MIN(Alias_ID), "
        "then summed per player - api-server matches player_statistics.php; not from fsl_matches):"
    ]
    for r in rows[:20]:
        nm = _pick_row_field(r, "Real_Name") or "?"
        pid = _pick_row_field(r, "Player_ID")
        mw = _pick_row_field(r, "total_maps_w", "total_maps_W")
        ml = _pick_row_field(r, "total_maps_l", "total_maps_L")
        pid_bit = f" id={pid}" if pid is not None else ""
        out.append(f"  {nm}{pid_bit}: {mw} map wins ({mw}-{ml} maps)")
    return "\n".join(out)


def _fmt_match_one(row: Optional[Dict[str, Any]]) -> str:
    if not row:
        return "Match not found."
    return (
        f"Match {row.get('fsl_match_id')}: {row.get('winner_name')} ({row.get('winner_race')}) "
        f"beat {row.get('loser_name')} ({row.get('loser_race')}) "
        f"{row.get('map_win')}-{row.get('map_loss')} maps, season {row.get('season')}."
    )


def _fmt_player_detail(db: Any, player_row: Dict[str, Any], stats_payload: Dict[str, Any]) -> str:
    pid = int(player_row["Player_ID"])
    stat_rows = stats_payload.get("statistics") or []
    team = player_row.get("Team_Name") or ""
    head = f"{player_row.get('Real_Name')} (id {pid})" + (f" team {team}" if team else "")
    cr = _pick_row_field(player_row, "Championship_Record")
    tlr = _pick_row_field(player_row, "TeamLeague_Championship_Record")
    intro = [head]
    if cr:
        intro.append(f"Championship record (Players DB): {cr}")
    if tlr:
        intro.append(f"Team league championship record (Players DB): {tlr}")
    if not stat_rows:
        return "\n".join(intro) + " — no FSL_STATISTICS rows."
    lines = intro + ["FSL stats (div/race maps sets):"]
    for s in stat_rows[:10]:
        lines.append(
            f"  {s.get('Division')}/{s.get('Race')}: "
            f"maps {s.get('MapsW', 0)}-{s.get('MapsL', 0)} "
            f"sets {s.get('SetsW', 0)}-{s.get('SetsL', 0)}"
        )
    return "\n".join(lines)


class FslAskAssistant:
    """Handles @-mention natural language → router LLM → FSL HTTP API."""

    def __init__(self, llm: ILanguageModel, db: Any):
        self._llm = llm
        self._db = db

    def enabled(self) -> bool:
        if getattr(config, "OPENAI_DISABLED", False):
            return False
        if not getattr(config, "ENABLE_FSL_ASK", False):
            return False
        return hasattr(self._db, "fsl_players_search") and callable(self._db.fsl_players_search)

    def _mentions_bot(self, text: str) -> bool:
        low = text.lower()
        owner = getattr(config, "OWNER", "").lower()
        page = getattr(config, "PAGE", "").lower()
        if owner and f"@{owner}" in low:
            return True
        if page and f"@{page}" in low:
            return True
        for extra in getattr(config, "FSL_ASK_EXTRA_MENTIONS", []) or []:
            if extra and str(extra).lower() in low:
                return True
        return False

    def _strip_to_question(self, text: str) -> str:
        t = text
        owner = getattr(config, "OWNER", "")
        page = getattr(config, "PAGE", "")
        for nick in (owner, page):
            if nick:
                t = re.sub(r"@?" + re.escape(nick) + r"\b", "", t, flags=re.I)
        for filler in ("hey", "hi", "yo", "please", "bot"):
            t = re.sub(r"^\s*" + filler + r"\b\s*", "", t, flags=re.I)
        return t.strip()

    def _keyword_gate_ok(self, question: str) -> bool:
        keys = getattr(config, "FSL_ASK_TRIGGER_KEYWORDS", None)
        if not keys:
            return True
        ql = question.lower()
        return any(k.lower() in ql for k in keys)

    async def _exec_action(self, action: str, params: Dict[str, Any]) -> Tuple[str, bool]:
        db = self._db
        loop = asyncio.get_running_loop()

        async def call(fn: Callable, *a, **kw):
            return await loop.run_in_executor(None, lambda: fn(*a, **kw))

        action = (action or "none").strip().lower()
        p = params or {}

        try:
            if action == "none":
                return "", True

            if action == "players_search":
                q = str(p.get("q", "")).strip()
                if not q:
                    return "Missing search text.", False
                lim = min(12, max(1, int(p.get("limit", 8))))
                data = await call(db.fsl_players_search, q, lim)
                return _fmt_players(data), True

            if action == "teams_search":
                q = str(p.get("q", "")).strip()
                lim = int(p.get("limit", 40 if not q else 12))
                lim = min(100, max(1, lim))
                data = await call(db.fsl_teams_search, q, lim)
                return _fmt_teams(data), True

            if action == "team_detail":
                name = str(p.get("name", "")).strip()
                if not name:
                    return "Missing team name.", False
                sr = await call(db.fsl_teams_search, name, 6)
                rows = sr.get("teams") or []
                if not rows:
                    return f"No FSL team matching {name!r}.", True
                tid = int(rows[0]["Team_ID"])
                row = await call(db.fsl_team_by_id, tid)
                if not row:
                    return "Team row not found after search.", True
                return _fmt_team_detail(row), True

            if action == "team_roster":
                name = str(p.get("name", "")).strip()
                if not name:
                    return "Missing team name.", False
                sr = await call(db.fsl_teams_search, name, 8)
                tr = sr.get("teams") or []
                if not tr:
                    return f"No FSL team matching {name!r}.", True
                tid = int(tr[0]["Team_ID"])
                team_row = await call(db.fsl_team_by_id, tid)
                if not team_row:
                    team_row = tr[0]
                roster = await call(db.fsl_team_players, tid)
                return _fmt_team_roster(team_row, roster), True

            if action == "schedule":
                season = p.get("season")
                week = p.get("week")
                lim = min(20, max(5, int(p.get("limit", 15))))
                data = await call(
                    db.fsl_schedule,
                    int(season) if season is not None else None,
                    int(week) if week is not None else None,
                    lim,
                )
                return _fmt_schedule(data), True

            if action == "team_league_season":
                season = p.get("season")
                if season is None:
                    return "team_league_season needs season (integer).", False
                sn = int(season)
                if not hasattr(db, "fsl_team_league_season_summary") or not callable(
                    getattr(db, "fsl_team_league_season_summary")
                ):
                    return (
                        "Team league season summary API not available on this database client.",
                        True,
                    )
                data = await call(db.fsl_team_league_season_summary, sn)
                return _fmt_team_league_season(data), True

            if action == "solo_division_season":
                dc = _normalize_solo_division_t_code(p.get("division"))
                if not dc:
                    return (
                        "solo_division_season needs division (Code S / Code A / Code B, or letter S/A/B).",
                        False,
                    )
                season = p.get("season")
                if season is None:
                    return "solo_division_season needs season (integer).", False
                sn = int(season)
                if not hasattr(db, "fsl_solo_division_season_standings") or not callable(
                    getattr(db, "fsl_solo_division_season_standings")
                ):
                    return (
                        "Solo division season standings API not available on this database client.",
                        True,
                    )
                data = await call(db.fsl_solo_division_season_standings, sn, dc)
                return _fmt_solo_division_season(data), True

            if action == "matches_h2h":
                pn = str(p.get("player_name", "")).strip()
                opp = str(p.get("opponent_name", "")).strip()
                if not pn or not opp:
                    return "matches_h2h needs player_name and opponent_name.", False
                season = p.get("season")
                sn = int(season) if season is not None else None
                if not hasattr(db, "fsl_matches_h2h") or not callable(
                    getattr(db, "fsl_matches_h2h")
                ):
                    return (
                        "Head-to-head summary API not available on this database client.",
                        True,
                    )
                data = await call(db.fsl_matches_h2h, pn, opp, sn)
                return _fmt_h2h_summary(data), True

            if action == "matches":
                pn = str(p.get("player_name", "")).strip()
                if not pn:
                    return "Missing player_name for matches.", False
                opp = str(p.get("opponent_name", "")).strip()
                season = p.get("season")
                sn = int(season) if season is not None else None
                if opp:
                    lim = min(150, max(5, int(p.get("limit", 120))))
                elif sn is not None:
                    lim = min(150, max(10, int(p.get("limit", 120))))
                else:
                    lim = min(150, max(5, int(p.get("limit", 25))))
                data = await loop.run_in_executor(
                    None,
                    lambda: db.fsl_matches(
                        season=sn,
                        player_name=pn,
                        player_id=None,
                        opponent_name=opp or None,
                        limit=lim,
                    ),
                )
                return (
                    _fmt_matches(
                        data,
                        player_name=pn,
                        opponent_name=opp if opp else None,
                        season=sn,
                    ),
                    True,
                )

            if action == "leaderboard_win_pct":
                mn = max(1, min(80, int(p.get("min_matches", 10))))
                lim = max(1, min(25, int(p.get("limit", 15))))
                data = await call(db.fsl_leaderboard_match_win_pct, mn, lim)
                return _fmt_leaderboard_win_pct(data), True

            if action == "leaderboard_total_wins":
                mn = max(1, min(80, int(p.get("min_matches", 1))))
                lim = max(1, min(25, int(p.get("limit", 15))))
                data = await call(db.fsl_leaderboard_match_total_wins, mn, lim)
                return _fmt_leaderboard_total_wins(data), True

            if action == "leaderboard_maps_won":
                lim = max(1, min(25, int(p.get("limit", 15))))
                data = await call(db.fsl_leaderboard_maps_won, lim)
                return _fmt_leaderboard_maps_won(data), True

            if action == "match_detail":
                mid = int(p.get("match_id", 0))
                if mid <= 0:
                    return "Invalid match id.", False
                row = await call(db.fsl_match_by_id, mid)
                return _fmt_match_one(row), True

            if action == "statistics_player":
                pid = int(p.get("player_id", 0))
                if pid <= 0:
                    return "Invalid player id.", False
                stats = await call(db.fsl_statistics_for_player, pid)
                return f"FSL statistics for player_id {pid}: " + json.dumps(
                    stats.get("statistics") or [], default=str
                )[:1200], True

            if action == "player_detail":
                name = str(p.get("name", "")).strip()
                if not name:
                    return "Missing player name.", False
                row = await call(db.fsl_player_by_name_exact, name)
                if not row:
                    sr = await call(db.fsl_players_search, name, 5)
                    rows = sr.get("players") or []
                    if not rows:
                        return f"No FSL player matching {name!r}.", True
                    row = rows[0]
                pid = int(row["Player_ID"])
                name_keep = row.get("Real_Name")
                full = await call(db.fsl_player_by_id, pid)
                if full:
                    row = {**full}
                    if name_keep:
                        row["Real_Name"] = name_keep
                stats = await call(db.fsl_statistics_for_player, pid)
                return _fmt_player_detail(db, row, stats), True

            return f"Unknown action {action!r}.", False
        except Exception as e:
            logger.exception("FSL exec error")
            return f"FSL lookup failed: {e}"[:300], True

    async def _format_answer(self, question: str, facts: str, action: str = "") -> str:
        extra = getattr(config, "FSL_ASK_SKIP_FORMAT_ACTIONS", None)
        skip_actions = _DEFAULT_SKIP_FORMAT_ACTIONS | (
            frozenset(extra) if isinstance(extra, (list, tuple, set)) else frozenset()
        )
        act = (action or "").strip().lower()
        if act == "solo_division_season":
            det = _draft_solo_division_champion_reply(facts, question)
            if det:
                return det
        if act in skip_actions:
            return facts
        if not getattr(config, "FSL_ASK_FORMAT_WITH_LLM", True):
            return facts
        prompt = (
            FSL_CHAT_DOMAIN_PREAMBLE
            + "\n\nYou help with Twitch chat. Reply in one short message (max 450 characters).\n"
            "READ THE QUESTION: answer it directly in the first sentence.\n"
            "- Solo division (Code S/A/B): **who won / champion / winner / took the title** → if FACTS contain "
            f"**{_OFFICIAL_CHAMP_MARKER}** with a player name, give **that** name as the official title holder "
            "(Players.Championship_Record). If that line is absent, use **First place / division leader(s), rank 1** "
            "for schedule W-L only - say standings are series record, not necessarily the stored title.\n"
            "Never say **no data** if either the official champion line or rank-1 standings names are present.\n"
            "- **2nd / runner-up** → **Second place player(s)** or rank 2 from FACTS.\n"
            "- Team league: champion → finals-week or standings row 1 as given in FACTS.\n"
            "Do not dump full standings unless the viewer asked for 'full standings' or 'table'. "
            "Use ONLY the FACTS — copy team/player names and W-L numbers EXACTLY as written; "
            "do not invent placements. If FACTS cannot answer the question, say what's missing.\n"
            "Abbreviations / casing: **champ** means **champion**; **Code S** and **code s** are the same division.\n"
            "Title fields (exact names): **`Players.Championship_Record`** (solo division champion text); "
            "**`Teams.TeamLeague_Championship_Record`** (team league org); **`Players.TeamLeague_Championship_Record`** (player team-league text).\n"
            "No emojis unless they appear in FACTS.\n\n"
            f"QUESTION: {question}\n\nFACTS:\n{facts}\n"
        )
        out = await self._llm.generate_raw(prompt)
        out = (out or "").strip()
        out = re.sub(r"[\r\n]+", " ", out)
        return out if out else facts

    async def try_handle(self, event: MessageEvent, chat_send) -> bool:
        """
        If this message should get an FSL NL reply, send it and return True.
        Return False to let nothing else in BotCore handle this message (caller should still skip legacy).
        """
        if event.platform != "twitch":
            return False
        if not self.enabled():
            return False
        if not self._mentions_bot(event.content):
            return False

        question = self._strip_to_question(event.content)
        if len(question) < 2:
            await chat_send(
                event.channel,
                tokensArray.truncate_to_byte_limit(
                    "Ask an FSL question after the mention, or type `fsl help` for commands.",
                    config.TWITCH_CHAT_BYTE_LIMIT,
                ),
            )
            return True

        if not self._keyword_gate_ok(question):
            await chat_send(
                event.channel,
                tokensArray.truncate_to_byte_limit(
                    getattr(
                        config,
                        "FSL_ASK_OFF_TOPIC_REPLY",
                        "Add an FSL keyword (league, schedule, player, team, match) or use `fsl help`.",
                    ),
                    config.TWITCH_CHAT_BYTE_LIMIT,
                ),
            )
            return True

        # Prefer schema-grounding path when enabled: fewer brittle router rules + no regex shim.
        use_grounding = getattr(config, "FSL_ASK_SCHEMA_GROUNDING", False)
        plan = None
        if not use_grounding:
            plan = _solo_h2h_plan_from_question(question)
            if plan:
                logger.debug("FSL NL: solo H2H pattern override → matches")
        if not plan:
            plan = _solo_division_season_plan_from_question(question)
            if plan:
                logger.debug("FSL NL: solo division pattern override → solo_division_season")
        if not plan:
            grounding_block = ""
            if use_grounding:
                g_prompt = SCHEMA_GROUNDING_PROMPT_TEMPLATE.replace(
                    "{question}", question.replace('"', "'")
                )
                raw_g = await self._llm.generate_raw(g_prompt)
                gt = (raw_g or "").strip()
                gt = re.sub(r"[\r\n]+", "\n", gt)
                if len(gt) > 900:
                    gt = gt[:900] + "…"
                if gt:
                    grounding_block = (
                        "Schema grounding (prior analysis — follow when choosing action):\n"
                        + gt
                        + "\n"
                    )
                    logger.debug("FSL NL: schema grounding step OK (%d chars)", len(gt))
            router_prompt = (
                ROUTER_PROMPT_TEMPLATE.replace("{question}", question.replace('"', "'")).replace(
                    "{schema_grounding_block}", grounding_block
                )
            )
            raw = await self._llm.generate_raw(router_prompt)
            plan = _extract_json_object(raw or "")
        if not plan or "action" not in plan:
            await chat_send(
                event.channel,
                tokensArray.truncate_to_byte_limit(
                    "Could not parse FSL plan; try a `fsl …` command from fsl help.",
                    config.TWITCH_CHAT_BYTE_LIMIT,
                ),
            )
            return True

        action = plan.get("action", "none")
        params = plan.get("params") if isinstance(plan.get("params"), dict) else {}

        if action == "none":
            msg = getattr(
                config,
                "FSL_ASK_NONE_REPLY",
                "That's not something I can look up in the FSL league database. Try: fsl help",
            )
            await chat_send(
                event.channel,
                tokensArray.truncate_to_byte_limit(msg, config.TWITCH_CHAT_BYTE_LIMIT),
            )
            return True

        facts, ok = await self._exec_action(action, params)
        if not ok and facts:
            await chat_send(
                event.channel,
                tokensArray.truncate_to_byte_limit(facts, config.TWITCH_CHAT_BYTE_LIMIT),
            )
            return True

        final_text = await self._format_answer(question, facts, action=action)
        await chat_send(
            event.channel,
            tokensArray.truncate_to_byte_limit(final_text, config.TWITCH_CHAT_BYTE_LIMIT),
        )
        return True

