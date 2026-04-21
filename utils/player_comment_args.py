"""Parse optional ReplayID or -N (games ago) prefix on player-comment text."""

from __future__ import annotations

import re
from typing import Optional, Tuple

# Leading integer (optionally negative), whitespace, then non-empty rest.
_REF_PREFIX_RE = re.compile(r"^(-?\d+)\s+(\S.*)$")


def split_replay_ref_prefix(body: str) -> Tuple[Optional[int], str]:
    """
    If body starts with a non-zero integer token followed by more text, treat the
    token as a replay reference: ReplayId if >0, or games-ago index if <0 (same
    convention as please retry / preview: -3 => third game before latest).

    Returns (ref_or_none, remainder). Leading 0 is not treated as a ref.
    """
    body = (body or "").strip()
    m = _REF_PREFIX_RE.match(body)
    if not m:
        return None, body
    ref = int(m.group(1))
    remainder = m.group(2).strip()
    if ref == 0:
        return None, body
    return ref, remainder
