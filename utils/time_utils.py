"""
Utility functions for time calculations.
"""
import re
from datetime import datetime
from typing import Optional

import pytz


def calculate_time_ago(date_played):
    """
    Calculate human-readable time since date.
    Accepts either a datetime object or a date string in format '%Y-%m-%d %H:%M:%S'.
    Returns 'about X hours ago' format.
    """
    eastern = pytz.timezone('US/Eastern')
    
    # Handle string input (from get_player_comments)
    if isinstance(date_played, str):
        if date_played == 'unknown' or not date_played:
            return date_played
        try:
            date_obj = datetime.strptime(date_played, '%Y-%m-%d %H:%M:%S')
            date_obj = eastern.localize(date_obj)
        except (ValueError, TypeError):
            return date_played
    else:
        # Handle datetime object (from database queries)
        if date_played.tzinfo is None:
            date_obj = eastern.localize(date_played)
        else:
            date_obj = date_played
    
    current_time_eastern = datetime.now(eastern)
    delta = current_time_eastern - date_obj
    
    days_ago = delta.days
    total_seconds = delta.total_seconds()
    
    if days_ago == 0:
        hours_ago = int(total_seconds // 3600)
        mins_ago = int((total_seconds % 3600) // 60)
        
        if hours_ago >= 1:
            return f"about {hours_ago} hour{'s' if hours_ago != 1 else ''} ago"
        elif mins_ago >= 1:
            return f"about {mins_ago} minute{'s' if mins_ago != 1 else ''} ago"
        else:
            return "just now"
    else:
        return f"about {days_ago} day{'s' if days_ago != 1 else ''} ago"


def parse_game_duration_seconds_from_summary(summary: Optional[str]) -> Optional[int]:
    """
    Extract game length in seconds from Replay_Summary text (e.g. 'Game Duration: 14m 15s').
    Returns None if not parseable.
    """
    if not summary or not isinstance(summary, str):
        return None
    # "Game Duration: 1h 5m 30s" etc.
    m = re.search(
        r"Game\s+Duration:\s*(\d+)\s*h(?:ours?)?\s+(\d+)\s*m(?:in)?\s+(\d+)\s*s(?:ec)?",
        summary,
        re.I,
    )
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    m = re.search(r"Game\s+Duration:\s*(\d+)\s*m(?:in(?:utes)?)?\s+(\d+)\s*s(?:ec(?:onds)?)?", summary, re.I)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.search(r"Game\s+Duration:\s*(\d+)\s*s(?:ec(?:onds)?)?\b", summary, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"Game\s+Duration:\s*(\d+)\s*m(?:in(?:utes)?)?\b", summary, re.I)
    if m:
        return int(m.group(1)) * 60
    return None

