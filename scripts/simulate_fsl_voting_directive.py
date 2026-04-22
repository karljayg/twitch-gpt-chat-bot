"""
Simulate Twitch admin directive: accept ratings <fsl_match_id>

Calls FSL voting API: match -> enable -> (optional) votes.
https://psistorm.com/fsl/docs/FSL_Voting_API_spec.md

Runs from repo root. Auth: uses FSL_VOTING_API_KEY if set, else settings.config
(FSL_VOTING_API_KEY or FSL_API_TOKEN). No env exports required for Git Bash.

Examples (Git Bash / cmd / PowerShell — same):
  python scripts/simulate_fsl_voting_directive.py --match-id 619
  python scripts/simulate_fsl_voting_directive.py --use-tunnel-test-match
  python scripts/simulate_fsl_voting_directive.py --match-id 619 --submit-votes --reviewer-id 1

Always writes UTF-8 log: logs/fsl_sim_directive_last_run.txt
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_BASE = "https://psistorm.com/fsl/api/voting.php"
VERIFY_SSL = False
LAST_RUN_LOG = os.path.join(_ROOT, "logs", "fsl_sim_directive_last_run.txt")


def _auth_session(base: str) -> tuple[requests.Session | None, list[str]]:
    lines: list[str] = []
    key = os.environ.get("FSL_VOTING_API_KEY")
    source = "env FSL_VOTING_API_KEY"
    if not key:
        try:
            from settings import config

            key = getattr(config, "FSL_VOTING_API_KEY", None)
            if key:
                source = "config.FSL_VOTING_API_KEY"
            if not key:
                key = getattr(config, "FSL_API_TOKEN", None)
                if key:
                    source = "config.FSL_API_TOKEN"
        except Exception as e:
            lines.append(f"config import failed: {e}")
            return None, lines
    if not key:
        lines.append(
            "No API key: set FSL_VOTING_API_KEY or add FSL_API_TOKEN in settings/config.py"
        )
        return None, lines
    lines.append(f"(auth: {source})")
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {key}"
    s.headers["Content-Type"] = "application/json"
    return s, lines


def _log(lines: list[str], title: str, resp: requests.Response) -> None:
    lines.append(f"\n=== {title} ===")
    lines.append(f"HTTP {resp.status_code}")
    try:
        lines.append(json.dumps(resp.json(), indent=2))
    except Exception:
        lines.append(resp.text[:2000])


def _sample_votes_payload() -> dict:
    """Synthetic chat tallies (pretend viewers voted)."""
    return {
        "micro": {"vote": 1, "tally": {"player1": 5, "player2": 2, "tie": 1}},
        "macro": {"vote": 2, "tally": {"player1": 1, "player2": 6, "tie": 0}},
        "clutch": {"vote": 0, "tally": {"player1": 3, "player2": 3, "tie": 2}},
        "creativity": {"vote": 1, "tally": {"player1": 4, "player2": 3, "tie": 0}},
        "aggression": {"vote": 2, "tally": {"player1": 2, "player2": 5, "tie": 0}},
        "strategy": {"vote": 1, "tally": {"player1": 5, "player2": 4, "tie": 1}},
    }


def _write_last_run(lines: list[str]) -> None:
    os.makedirs(os.path.dirname(LAST_RUN_LOG), exist_ok=True)
    text = "\n".join(lines)
    with open(LAST_RUN_LOG, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"\n[Wrote UTF-8 log: {LAST_RUN_LOG}]\n")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Simulate accept ratings <fsl_match_id> against FSL voting API.")
    p.add_argument(
        "match_id_positional",
        nargs="?",
        default="",
        help="fsl_match_id (optional if --match-id is set)",
    )
    p.add_argument("-m", "--match-id", default="", help="FSL fsl_match_id")
    p.add_argument(
        "--submit-votes",
        action="store_true",
        help="POST synthetic tallies after enable (needs --reviewer-id or config)",
    )
    p.add_argument("--reviewer-id", default="", help="reviewers.id for TwitchChat bot row")
    p.add_argument(
        "--base-url",
        default="",
        help="Override voting API base (default from env FSL_VOTING_API_URL or built-in)",
    )
    p.add_argument(
        "--use-tunnel-test-match",
        action="store_true",
        help="Use config.FSL_TUNNEL_TEST_MATCH_ID (default 99001 Freeedom vs SirMalagant)",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    lines: list[str] = []

    mid_s = ""
    if getattr(args, "use_tunnel_test_match", False):
        try:
            from settings import config as _cfg

            tid = getattr(_cfg, "FSL_TUNNEL_TEST_MATCH_ID", None)
            if tid is not None:
                mid_s = str(int(tid))
        except Exception:
            pass
    if not mid_s:
        mid_s = (
            args.match_id.strip()
            or args.match_id_positional.strip()
            or os.environ.get("FSL_TEST_MATCH_ID", "").strip()
        )
    if not mid_s:
        msg = (
            "Missing match id: use --match-id N, pass N as arg, "
            "FSL_TEST_MATCH_ID env, or --use-tunnel-test-match."
        )
        print(msg)
        return 1

    submit = args.submit_votes or (os.environ.get("FSL_SIM_SUBMIT_VOTES") == "1")

    rid_s = (args.reviewer_id or os.environ.get("FSL_BOT_REVIEWER_ID", "")).strip()
    if not rid_s:
        try:
            from settings import config

            rid_s = str(getattr(config, "FSL_BOT_REVIEWER_ID", "") or "").strip()
        except Exception:
            pass

    base = (
        args.base_url.strip()
        or os.environ.get("FSL_VOTING_API_URL", "").strip()
        or DEFAULT_BASE
    )
    try:
        from settings import config

        base = getattr(config, "FSL_VOTING_API_URL", None) or base
    except Exception:
        pass
    base = base.rstrip("?&")

    session, auth_lines = _auth_session(base)
    lines.extend(auth_lines)
    lines.append(f"Base: {base}")
    lines.append(f"\n>>> DIRECTIVE: accept ratings {mid_s} (simulated)\n")

    if not session:
        _write_last_run(lines)
        print("\n".join(lines))
        return 1

    mid = int(mid_s)

    r_match = session.get(
        f"{base}?action=match&fsl_match_id={mid}",
        timeout=20,
        verify=VERIFY_SSL,
    )
    _log(lines, "1) GET match (confirm players / division)", r_match)
    if r_match.status_code != 200:
        _write_last_run(lines)
        print("\n".join(lines))
        return 1

    body_enable = {
        "fsl_match_id": mid,
        "requested_by": "simulate_fsl_voting_directive.py",
        "channel": "simulation",
    }
    r_en = session.post(
        f"{base}?action=enable",
        json=body_enable,
        timeout=20,
        verify=VERIFY_SSL,
    )
    _log(lines, "2) POST enable (open 5m window)", r_en)

    r_act = session.get(f"{base}?action=active", timeout=20, verify=VERIFY_SSL)
    _log(lines, "3) GET active (session check)", r_act)

    if not submit:
        lines.append("\n(Add --submit-votes --reviewer-id N to POST votes.)")
        _write_last_run(lines)
        print("\n".join(lines))
        return 0

    if not rid_s:
        lines.append("\n--submit-votes requires --reviewer-id or FSL_BOT_REVIEWER_ID in config/env.")
        _write_last_run(lines)
        print("\n".join(lines))
        return 1

    try:
        en_data = r_en.json().get("data") or {}
        session_id = en_data.get("session_id")
    except Exception:
        session_id = None
    if not session_id:
        lines.append("\nNo session_id from enable response — skip POST votes.")
        _write_last_run(lines)
        print("\n".join(lines))
        return 1

    vote_body = {
        "session_id": session_id,
        "fsl_match_id": mid,
        "reviewer_id": int(rid_s),
        "votes": _sample_votes_payload(),
    }
    r_v = session.post(
        f"{base}?action=votes",
        json=vote_body,
        timeout=20,
        verify=VERIFY_SSL,
    )
    _log(lines, "4) POST votes (synthetic chat tallies)", r_v)

    code = 0 if r_v.status_code == 200 else 1
    _write_last_run(lines)
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
