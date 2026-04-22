"""
Temporary probe for FSL voting API (voting.php).
https://psistorm.com/fsl/docs/FSL_Voting_API_spec.md

Usage (PowerShell):
  $env:FSL_VOTING_API_KEY = "your-bearer-token"
  $env:FSL_TEST_MATCH_ID = "12345"   # optional, for GET match
  $env:FSL_VOTING_TEST_WRITE = "1"  # optional, tries POST enable (side effects)
  python scripts/temp_test_fsl_voting_api.py > fsl_voting_test_output.txt 2>&1
"""
from __future__ import annotations

import json
import os
import sys

# Repo root (parent of scripts/) on sys.path for `import settings`
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import requests

import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_BASE = "https://psistorm.com/fsl/api/voting.php"
VERIFY_SSL = False


def main() -> int:
    lines: list[str] = []
    base = os.environ.get("FSL_VOTING_API_URL", DEFAULT_BASE).rstrip("?&")
    key = os.environ.get("FSL_VOTING_API_KEY")
    if not key:
        try:
            from settings import config

            key = getattr(config, "FSL_VOTING_API_KEY", None)
            if not key:
                key = getattr(config, "FSL_API_TOKEN", None)
                if key:
                    lines.append("(auth: config.FSL_API_TOKEN)")
        except Exception as e:
            print("No FSL_VOTING_API_KEY env and config import failed:", e)
            key = None
    lines.append(f"URL base: {base}")
    lines.append(f"Key present: {bool(key)} (len={len(key) if key else 0})")

    session = requests.Session()
    session.headers["Content-Type"] = "application/json"
    if key:
        session.headers["Authorization"] = f"Bearer {key}"

    def log(title: str, resp: requests.Response) -> None:
        lines.append(f"\n=== {title} ===")
        lines.append(f"HTTP {resp.status_code}")
        try:
            lines.append(json.dumps(resp.json(), indent=2))
        except Exception:
            lines.append(resp.text[:2000])

    # 1) No auth sanity (expect 401)
    r0 = requests.get(f"{base}?action=active", timeout=15, verify=VERIFY_SSL)
    log("GET active (no Authorization header)", r0)

    if not key:
        lines.append("\nSet FSL_VOTING_API_KEY or FSL_API_TOKEN in settings/config.py")
        print("\n".join(lines))
        return 1

    # 2) Authenticated active
    r1 = session.get(f"{base}?action=active", timeout=15, verify=VERIFY_SSL)
    log("GET ?action=active (with Bearer)", r1)

    match_id = os.environ.get("FSL_TEST_MATCH_ID", "").strip()
    if match_id:
        r2 = session.get(
            f"{base}?action=match&fsl_match_id={match_id}",
            timeout=15,
            verify=VERIFY_SSL,
        )
        log(f"GET ?action=match&fsl_match_id={match_id}", r2)

    if os.environ.get("FSL_VOTING_TEST_WRITE") == "1" and match_id:
        body = {
            "fsl_match_id": int(match_id),
            "requested_by": "temp_test_fsl_voting_api",
            "channel": "test",
        }
        r3 = session.post(
            f"{base}?action=enable",
            json=body,
            timeout=15,
            verify=VERIFY_SSL,
        )
        log("POST ?action=enable", r3)
    elif os.environ.get("FSL_VOTING_TEST_WRITE") == "1":
        lines.append("\nFSL_VOTING_TEST_WRITE=1 skipped: set FSL_TEST_MATCH_ID for enable.")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
