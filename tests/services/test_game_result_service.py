import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from models.game_info import GameInfo
from core.game_result_service import GameResultService
from core.interfaces import IReplayRepository

@pytest.fixture
def mock_repo():
    repo = MagicMock(spec=IReplayRepository)
    repo.save_replay = AsyncMock(return_value=True)
    return repo

@pytest.fixture
def mock_chat_service():
    service = MagicMock()
    service.send_message = AsyncMock()
    service.platform = "twitch"
    return service

@pytest.fixture
def mock_pattern_learner():
    learner = MagicMock()
    learner.process_game_result = MagicMock()
    return learner

@pytest.mark.asyncio
async def test_process_game_result_flow(mock_repo, mock_chat_service, mock_pattern_learner):
    service = GameResultService(mock_repo, [mock_chat_service], mock_pattern_learner)
    
    # Patch asyncio.sleep to run instantly
    with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        # Patch internal methods to avoid FS/Parsing
        with patch.object(service, '_find_replay_file', return_value="C:/Replays/test.SC2Replay") as mock_find, \
             patch.object(service, '_parse_replay', return_value={"map": "TestMap", "players": {}}) as mock_parse:
            
            game_data = {
                "isReplay": False,
                "displayTime": 10.0,
                "players": [
                    {"name": "Streamer", "result": "Victory", "race": "Protoss", "type": "user"},
                    {"name": "Opponent", "result": "Defeat", "race": "Zerg", "type": "user"}
                ]
            }
            game_info = GameInfo(game_data)
            
            await service.process_game_end(game_info)
            
            # Verify sleep was called
            mock_sleep.assert_called_with(10)
            
            # Verify we found and parsed replay
            mock_find.assert_called()
            mock_parse.assert_called_with("C:/Replays/test.SC2Replay")
            
            # Verify DB insert via Repository
            mock_repo.save_replay.assert_called()
            args, _ = mock_repo.save_replay.call_args
            assert isinstance(args[0], str)
            assert "Winners: Streamer" in args[0]
            
            # Verify chat announcement
            mock_chat_service.send_message.assert_called()
            
            # Verify state update
            assert service.last_processed_replay == "C:/Replays/test.SC2Replay"

@pytest.mark.asyncio
async def test_process_game_result_no_replay(mock_repo, mock_chat_service, mock_pattern_learner):
    service = GameResultService(mock_repo, [mock_chat_service], mock_pattern_learner)
    
    with patch('asyncio.sleep', new_callable=AsyncMock):
        with patch.object(service, '_find_replay_file', return_value=None):
            
            game_data = {"isReplay": False, "displayTime": 10.0, "players": []}
            game_info = GameInfo(game_data)
            
            await service.process_game_end(game_info)
            
            # Should exit early without updating last_processed_replay
            assert service.last_processed_replay is None
            
            # DB should NOT be called
            mock_repo.save_replay.assert_not_called()
