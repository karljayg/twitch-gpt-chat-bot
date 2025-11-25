import pytest
from core.game_summarizer import GameSummarizer
from unittest.mock import MagicMock

def test_generate_summary_basic():
    replay_data = {
        "players": {
            1: {"name": "Player1", "race": "Zerg", "unitsLost": [], "buildOrder": []},
            2: {"name": "Player2", "race": "Terran", "unitsLost": [], "buildOrder": []}
        },
        "region": "us",
        "game_type": "1v1",
        "unix_timestamp": 1234567890,
        "map": "Test Map",
        "frames": 960,  # 60 seconds at 16 fps
        "frames_per_second": 16
    }
    
    summary = GameSummarizer.generate_summary(replay_data, "Player1", "Player2")
    
    assert "Players: Player1: Zerg, Player2: Terran" in summary
    assert "Map: Test Map" in summary
    assert "Game Duration: 1m 0s" in summary
    assert "Winners: Player1" in summary

def test_calculate_duration():
    replay_data = {"frames": 1600, "frames_per_second": 16}
    duration = GameSummarizer.calculate_duration(replay_data)
    assert duration["totalSeconds"] == 100.0
    assert duration["gameDuration"] == "1m 40s"

def test_anonymize_names():
    # Test that streamer name replacement works (mocking config)
    # We'll have to patch config in the implementation
    pass 


