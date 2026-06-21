"""Typed views over the Stream Production Status API JSON.

These are thin, defensive wrappers: the producer's browser pushes state, so any
field can be missing or null. Everything degrades to safe defaults.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class StreamEvent:
    """One entry from `recent_events` / the day log."""
    id: int
    at: str
    type: str
    data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, d: Dict[str, Any]) -> "StreamEvent":
        d = d or {}
        return cls(
            id=int(d.get("id", 0) or 0),
            at=str(d.get("at", "") or ""),
            type=str(d.get("type", "") or ""),
            data=d.get("data") or {},
        )

    def dedup_key(self) -> str:
        # `id` resets to 1 each new day file, so key on date + id to survive midnight.
        return f"{self.at[:10]}#{self.id}"


@dataclass
class StatusSnapshot:
    """Snapshot returned by GET /status (and /status?since=)."""
    seq: int = 0
    stream_alive: bool = False
    heartbeat_age_ms: Optional[int] = None
    scene: Dict[str, Any] = field(default_factory=dict)
    music: Dict[str, Any] = field(default_factory=dict)
    match: Dict[str, Any] = field(default_factory=dict)
    player_intro: Dict[str, Any] = field(default_factory=dict)
    gg: Dict[str, Any] = field(default_factory=dict)
    recent_events: List[StreamEvent] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, d: Dict[str, Any]) -> "StatusSnapshot":
        d = d or {}
        return cls(
            seq=int(d.get("seq", 0) or 0),
            stream_alive=bool(d.get("stream_alive", False)),
            heartbeat_age_ms=d.get("heartbeat_age_ms"),
            scene=d.get("scene") or {},
            music=d.get("music") or {},
            match=d.get("match") or {},
            player_intro=d.get("player_intro") or {},
            gg=d.get("gg") or {},
            recent_events=[StreamEvent.from_json(e) for e in (d.get("recent_events") or [])],
            raw=d,
        )

    def team_names(self) -> Tuple[Optional[str], Optional[str]]:
        a = (self.match.get("team_a") or {}).get("name")
        b = (self.match.get("team_b") or {}).get("name")
        return a, b

    def team_scores(self) -> Tuple[Any, Any]:
        a = (self.match.get("team_a") or {}).get("score")
        b = (self.match.get("team_b") or {}).get("score")
        return a, b

    def series_winner(self) -> Optional[str]:
        return self.match.get("series_winner")

    def active_scene(self) -> Optional[str]:
        return self.scene.get("active")

    def team_name_for(self, team_key: Optional[str]) -> Optional[str]:
        if team_key == "a":
            return (self.match.get("team_a") or {}).get("name")
        if team_key == "b":
            return (self.match.get("team_b") or {}).get("name")
        return None
