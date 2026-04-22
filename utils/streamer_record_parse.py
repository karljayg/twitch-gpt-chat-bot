"""
Parse win/loss lines from Database.get_player_records() for streamer vs opponent.

Rows look like: "Timthehappy, KJ, 5 wins, 3 losses"
First field = player queried; second = opponent; wins/losses are the FIRST player's.
"""

import re
from typing import List, Optional, Tuple

from settings import config


def parse_streamer_record_vs_opponent(raw_records: Optional[List[str]]) -> Optional[Tuple[int, int]]:
    """
    Returns (streamer_wins, streamer_losses) vs the opponent named in get_player_records,
    or None if no row matches a streamer account as the opponent.

    Uses SC2_PLAYER_ACCOUNTS, SC2_BARCODE_ACCOUNTS, and STREAMER_NICKNAME for matching.
    """
    if not raw_records:
        return None

    streamer_ids = [a.lower() for a in config.SC2_PLAYER_ACCOUNTS]
    streamer_ids.extend([a.lower() for a in getattr(config, "SC2_BARCODE_ACCOUNTS", [])])
    if getattr(config, "STREAMER_NICKNAME", None):
        streamer_ids.append(config.STREAMER_NICKNAME.lower())
    streamer_ids = list(dict.fromkeys(streamer_ids))

    pat = re.compile(
        r"^\s*([^,]+)\s*,\s*([^,]+)\s*,\s*(\d+)\s+wins?\s*,\s*(\d+)\s+losses?\s*$",
        re.IGNORECASE,
    )

    for row in raw_records:
        m = pat.match(row.strip())
        if not m:
            continue
        opp = m.group(2).strip()
        if opp.lower() not in streamer_ids:
            continue
        first_wins = int(m.group(3))
        first_losses = int(m.group(4))
        # first column is opponent-from-DB query (their wins / losses); streamer is second column
        streamer_wins = first_losses
        streamer_losses = first_wins
        return streamer_wins, streamer_losses

    return None
