from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class BaseEvent:
    """Base class for all bot events"""
    pass

@dataclass
class MessageEvent(BaseEvent):
    """Event triggered when a chat message is received"""
    platform: str
    channel: str
    author: str
    content: str
    raw_data: Any = None

@dataclass
class GameStateEvent(BaseEvent):
    """Event triggered when SC2 game state changes"""
    event_type: str  # e.g., "game_started", "game_ended"
    data: Any = None


