"""
Utility functions for time calculations.
"""
from datetime import datetime
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

