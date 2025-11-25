import pytest
from unittest.mock import MagicMock
from core.audio_service import AudioService

@pytest.fixture
def mock_tts():
    module = MagicMock()
    module.speak_text = MagicMock()
    return module

@pytest.fixture
def mock_sound_player():
    player = MagicMock()
    player.play_sound = MagicMock()
    return player

@pytest.mark.asyncio
async def test_speak_success(mock_tts, mock_sound_player):
    service = AudioService(mock_sound_player, mock_tts)
    await service.speak("Test Message")
    # Confirms run_in_executor called the mock
    mock_tts.speak_text.assert_called_with("Test Message")

@pytest.mark.asyncio
async def test_speak_no_module(mock_sound_player):
    service = AudioService(mock_sound_player, None)
    # Should not raise error
    await service.speak("Test Message")

@pytest.mark.asyncio
async def test_play_sound_success(mock_tts, mock_sound_player):
    service = AudioService(mock_sound_player, mock_tts)
    await service.play_sound("game_start")
    # Check calls. legacy play_sound takes (key, logger)
    mock_sound_player.play_sound.assert_called()
    args, _ = mock_sound_player.play_sound.call_args
    assert args[0] == "game_start"

@pytest.mark.asyncio
async def test_play_sound_no_player(mock_tts):
    service = AudioService(None, mock_tts)
    await service.play_sound("game_start")
    # Should not raise error


