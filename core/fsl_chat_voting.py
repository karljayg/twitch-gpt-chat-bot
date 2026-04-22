"""
FSL spider chat voting: capture Twitch lines during an open session, POST tallies to voting API.
https://psistorm.com/fsl/docs/FSL_Voting_API_spec.md
"""
from __future__ import annotations

import json
import logging
import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, DefaultDict, Dict, List, Literal, Optional, Set, Tuple

import requests
import urllib3

from settings import config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# token -> (attribute, vote_side) vote_side: '1' player1, '2' player2, '0' tie
VOTE_TOKEN_MAP: Dict[str, Tuple[str, str]] = {
    "mic1": ("micro", "1"),
    "mic2": ("micro", "2"),
    "mict": ("micro", "0"),
    "mac1": ("macro", "1"),
    "mac2": ("macro", "2"),
    "mact": ("macro", "0"),
    "clu1": ("clutch", "1"),
    "clu2": ("clutch", "2"),
    "clut": ("clutch", "0"),
    "cre1": ("creativity", "1"),
    "cre2": ("creativity", "2"),
    "cret": ("creativity", "0"),
    "agg1": ("aggression", "1"),
    "agg2": ("aggression", "2"),
    "aggt": ("aggression", "0"),
    "str1": ("strategy", "1"),
    "str2": ("strategy", "2"),
    "strt": ("strategy", "0"),
}

ALL_VOTE_TOKENS: Set[str] = set(VOTE_TOKEN_MAP)
ATTRIBUTES: Tuple[str, ...] = (
    "micro",
    "macro",
    "clutch",
    "creativity",
    "aggression",
    "strategy",
)


def _voting_base_url() -> str:
    return (
        getattr(config, "FSL_VOTING_API_URL", None)
        or "https://psistorm.com/fsl/api/voting.php"
    ).rstrip("?&")


def _voting_bearer() -> Optional[str]:
    return getattr(config, "FSL_VOTING_API_KEY", None) or getattr(
        config, "FSL_API_TOKEN", None
    )


def _verify_ssl() -> bool:
    return getattr(config, "FSL_VOTING_VERIFY_SSL", getattr(config, "FSL_VERIFY_SSL", True))


class FSLChatVotingSession:
    """One active window; thread-safe record + delayed submit."""

    def __init__(
        self,
        *,
        fsl_match_id: int,
        session_id: int,
        expires_at_iso: str,
        player1_name: str,
        player2_name: str,
        twitch_bot: Any,
    ) -> None:
        self.fsl_match_id = fsl_match_id
        self.session_id = session_id
        self.expires_at_iso = expires_at_iso
        self.player1_name = player1_name
        self.player2_name = player2_name
        self._twitch_bot = twitch_bot
        self._lock = threading.Lock()
        # user_lower -> attr -> '1'|'2'|'0' (last token wins per user per attribute)
        self._votes: DefaultDict[str, Dict[str, str]] = defaultdict(dict)
        self._timer: Optional[threading.Timer] = None
        self._closed = False
        self._long_help_emitted = False

    def is_active(self) -> bool:
        with self._lock:
            return not self._closed

    def try_claim_long_help(self) -> bool:
        """If long !ratings text was not yet sent this session, mark sent and return True."""
        with self._lock:
            if self._long_help_emitted:
                return False
            self._long_help_emitted = True
            return True

    def cancel_timer(self) -> None:
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None

    def schedule_auto_submit(self) -> None:
        try:
            exp = datetime.fromisoformat(
                self.expires_at_iso.replace("Z", "+00:00")
            )
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
        except Exception as e:
            logger.error(f"FSL voting: bad expires_at {self.expires_at_iso!r}: {e}")
            return

        now = datetime.now(timezone.utc)
        until_exp = (exp - now).total_seconds()
        try:
            buffer = float(getattr(config, "FSL_VOTING_SUBMIT_BUFFER_SEC", 15.0) or 0.0)
        except (TypeError, ValueError):
            buffer = 15.0
        buffer = max(0.0, min(buffer, 120.0))
        delay = until_exp - buffer
        delay = max(1.0, min(delay, 3600.0))

        def _fire() -> None:
            self.submit_final(reason="session timer")

        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(delay, _fire)
            self._timer.daemon = True
            self._timer.start()
        logger.info(
            f"FSL voting: auto-submit in {delay:.0f}s "
            f"(~{buffer:.0f}s before expires_at, {until_exp:.0f}s until API expiry; {self.expires_at_iso})"
        )

    def record_chat_line(
        self, user_login_lower: str, message: str
    ) -> Literal["none", "partial", "consume"]:
        """
        Parse whitespace tokens; known vote tokens update last-wins map.
        Returns consume if every token was a vote token (skip legacy chat).
        """
        raw = message.strip()
        if not raw:
            return "none"
        tokens = raw.lower().split()
        recognized: List[str] = []
        unrecognized: List[str] = []
        for t in tokens:
            if t in VOTE_TOKEN_MAP:
                recognized.append(t)
            else:
                unrecognized.append(t)
        if not recognized:
            return "none"
        with self._lock:
            if self._closed:
                return "none"
            umap = self._votes[user_login_lower]
            for t in recognized:
                attr, side = VOTE_TOKEN_MAP[t]
                umap[attr] = side
                logger.info(
                    f"[FSL voting] {user_login_lower} -> {attr} = player{side} (token {t})"
                )
        if unrecognized:
            return "partial"
        return "consume"

    def build_votes_body(self, reviewer_id: int) -> dict:
        body_votes: Dict[str, Any] = {}
        with self._lock:
            snap = {u: dict(m) for u, m in self._votes.items()}
        for attr in ATTRIBUTES:
            p1 = p2 = t = 0
            for _u, umap in snap.items():
                v = umap.get(attr)
                if v == "1":
                    p1 += 1
                elif v == "2":
                    p2 += 1
                elif v == "0":
                    t += 1
            if p1 > p2 and p1 >= t:
                maj = 1
            elif p2 > p1 and p2 >= t:
                maj = 2
            else:
                maj = 0
            body_votes[attr] = {
                "vote": maj,
                "tally": {"player1": p1, "player2": p2, "tie": t},
            }
        return {
            "session_id": self.session_id,
            "fsl_match_id": self.fsl_match_id,
            "reviewer_id": reviewer_id,
            "votes": body_votes,
        }

    def _short_summary_parts(self) -> List[str]:
        rid = int(getattr(config, "FSL_BOT_REVIEWER_ID", 0) or 0)
        if not rid:
            return []
        body = self.build_votes_body(rid)
        parts = []
        for attr in ATTRIBUTES:
            b = body["votes"].get(attr, {})
            t = b.get("tally", {})
            parts.append(
                f"{attr[:3]}:{b.get('vote')}({t.get('player1')}/{t.get('player2')}/{t.get('tie')})"
            )
        return parts

    def summary_lines(self) -> List[str]:
        rid = int(getattr(config, "FSL_BOT_REVIEWER_ID", 0) or 0)
        body = self.build_votes_body(rid) if rid else {"votes": {}}
        lines = [
            f"match={self.fsl_match_id} session={self.session_id} "
            f"P1={self.player1_name} P2={self.player2_name}"
        ]
        for attr in ATTRIBUTES:
            b = body["votes"].get(attr, {})
            t = b.get("tally", {})
            lines.append(
                f"  {attr}: vote={b.get('vote')} tallies p1={t.get('player1')} "
                f"p2={t.get('player2')} tie={t.get('tie')}"
            )
        return lines

    def submit_final(self, reason: str) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            if self._timer:
                self._timer.cancel()
                self._timer = None

        for line in self.summary_lines():
            logger.info(f"[FSL voting] tally {line}")

        key = _voting_bearer()
        if not key:
            logger.error("FSL voting submit: no API token")
            self._emit_chat("FSL voting: missing API token; votes not submitted.")
            self._detach_bot()
            return
        rid = getattr(config, "FSL_BOT_REVIEWER_ID", None)
        if not rid:
            logger.error("FSL voting submit: FSL_BOT_REVIEWER_ID not set")
            self._emit_chat("FSL voting: FSL_BOT_REVIEWER_ID not set; votes not submitted.")
            self._detach_bot()
            return

        base = _voting_base_url()
        payload = self.build_votes_body(int(rid))
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        try:
            r = requests.post(
                f"{base}?action=votes",
                json=payload,
                headers=headers,
                timeout=20,
                verify=_verify_ssl(),
            )
            logger.info(
                f"FSL voting POST votes ({reason}): HTTP {r.status_code} {r.text[:500]}"
            )
            if r.status_code == 200:
                msg = (
                    f"Ratings submitted ({reason}). "
                    + " | ".join(self._short_summary_parts())
                )
                self._emit_chat(msg[: config.TWITCH_CHAT_BYTE_LIMIT])
            else:
                self._emit_chat(
                    f"Ratings submit failed HTTP {r.status_code} ({reason}). Check logs."
                )
        except Exception as e:
            logger.exception(f"FSL voting POST failed: {e}")
            self._emit_chat(f"Ratings submit error ({reason}): {e}")

        self._detach_bot()

    def _emit_chat(self, text: str) -> None:
        tb = self._twitch_bot
        if tb and hasattr(tb, "send_channel_message_sync"):
            try:
                tb.send_channel_message_sync(text)
            except Exception as e:
                logger.error(f"FSL voting chat emit failed: {e}")

    def _detach_bot(self) -> None:
        tb = self._twitch_bot
        if tb and getattr(tb, "fsl_voting_session", None) is self:
            tb.fsl_voting_session = None


def api_get_match(fsl_match_id: int) -> Tuple[Optional[dict], Optional[str]]:
    key = _voting_bearer()
    if not key:
        return None, "No FSL_VOTING_API_KEY / FSL_API_TOKEN"
    base = _voting_base_url()
    try:
        r = requests.get(
            f"{base}?action=match&fsl_match_id={fsl_match_id}",
            headers={"Authorization": f"Bearer {key}"},
            timeout=20,
            verify=_verify_ssl(),
        )
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}: {r.text[:200]}"
        j = r.json()
        if not j.get("ok"):
            return None, json.dumps(j)[:300]
        return j.get("data"), None
    except Exception as e:
        return None, str(e)


def api_post_enable(
    fsl_match_id: int, requested_by: str, channel: str
) -> Tuple[Optional[dict], Optional[str]]:
    key = _voting_bearer()
    if not key:
        return None, "No FSL_VOTING_API_KEY / FSL_API_TOKEN"
    base = _voting_base_url()
    body = {
        "fsl_match_id": fsl_match_id,
        "requested_by": requested_by,
        "channel": channel,
    }
    try:
        r = requests.post(
            f"{base}?action=enable",
            json=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            timeout=20,
            verify=_verify_ssl(),
        )
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}: {r.text[:300]}"
        j = r.json()
        if not j.get("ok"):
            return None, json.dumps(j)[:300]
        return j.get("data"), None
    except Exception as e:
        return None, str(e)


def _clip_twitch_chat(text: str, byte_limit: int) -> str:
    """Twitch counts bytes; avoid cutting mid-character."""
    raw = text.encode("utf-8")
    if len(raw) <= byte_limit:
        return text
    return raw[:byte_limit].decode("utf-8", errors="ignore").rstrip()


def clip_chat_message(text: str) -> str:
    lim = int(getattr(config, "TWITCH_CHAT_BYTE_LIMIT", 450) or 450)
    return _clip_twitch_chat(text, lim)


def short_ratings_open_message(p1: str, p2: str) -> str:
    """One line after accept ratings (minimal clutter)."""
    return (
        f"Ratings OPEN for this last game between {p1}(P1) vs {p2}(P2). "
        f"Vote on attributes: mic=micro, mac=macro, clu=clutch, cre=creativity, agg=aggression, str=strategy  "
        f"For more info, type !ratings"
    )


def _split_chat_utf8(text: str, byte_limit: int) -> List[str]:
    """Split text into Twitch-safe chunks without breaking UTF-8."""
    if not text:
        return []
    out: List[str] = []
    remaining = text
    while remaining:
        piece = _clip_twitch_chat(remaining, byte_limit)
        if not piece:
            break
        out.append(piece)
        b = remaining.encode("utf-8")
        pb = piece.encode("utf-8")
        if len(pb) >= len(b):
            break
        remaining = b[len(pb) :].decode("utf-8", errors="ignore").lstrip()
    return out


def long_ratings_help_chunks(p1: str, p2: str) -> List[str]:
    """Full !ratings text: intro + codes (split for Twitch byte limit)."""
    lim = int(getattr(config, "TWITCH_CHAT_BYTE_LIMIT", 450) or 450)
    intro = (
        "FSL spider chart: each player is scored on six skills (micro, macro, clutch, creativity, aggression, strategy) "
        "for the division chart. Chat votes you send here are rolled up into one official bot vote for this match, "
        "so you are judging both players on those axes (not only who won the series). "
        "P1 is the player recorded as this match's winner on the FSL card; P2 is the other player. "
        "Type short codes alone or on one line; until the window closes you can change your mind — last code per skill wins."
    )
    technical = (
        f"Ratings OPEN — {p1}(P1) vs {p2}(P2) | INSTRUCTIONS: use 3-letter attr + 1/2/t (1=P1, 2=P2, t=tie) | "
        "ATTRS: mic=micro, mac=macro, clu=clutch, cre=creativity, agg=aggression, str=strategy | "
        "EXAMPLE: mic1 mac2 clut cre1 (P1 micro, P2 macro, tie clutch, P1 creativity) | last vote per attr counts"
    )
    return _split_chat_utf8(intro, lim) + _split_chat_utf8(technical, lim)
