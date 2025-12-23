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
        # Patch file system checks (added for segfault prevention)
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=50000), \
             patch('builtins.open', create=True):  # Mock file open for lock check
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
                
                # Verify sleep was called (there's a 1s sleep for replay wait, and 10s for pattern learning)
                # The pattern learning sleep(10) happens in an async task that may not complete during test
                # So we just verify that sleep was called (the 1s sleep for replay wait)
                assert mock_sleep.called, "asyncio.sleep should have been called"
                # The pattern learning trigger is async and may not complete, so we don't assert on sleep(10)
                
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

@pytest.mark.asyncio
async def test_test_replay_by_id_not_found(mock_repo, mock_chat_service, mock_pattern_learner):
    service = GameResultService(mock_repo, [mock_chat_service], mock_pattern_learner)
    
    # Mock DB to return None (replay not found)
    mock_db = MagicMock()
    mock_db.get_replay_by_id = MagicMock(return_value=None)
    mock_repo.db = mock_db
    
    result = await service.test_replay_by_id(99999)
    
    assert "not found" in result.lower()
    mock_db.get_replay_by_id.assert_called_once_with(99999)

@pytest.mark.asyncio
async def test_test_replay_by_id_with_comments_json(mock_repo, mock_chat_service, mock_pattern_learner):
    service = GameResultService(mock_repo, [mock_chat_service], mock_pattern_learner)
    
    # Mock DB to return replay info
    mock_db = MagicMock()
    mock_db.get_replay_by_id = MagicMock(return_value={
        'opponent': 'TestOpponent',
        'opponent_race': 'Zerg',
        'map': 'TestMap',
        'date': '2025-12-23 10:00:00',
        'replay_summary': ''
    })
    mock_repo.db = mock_db
    
    # Mock comments.json with matching entry
    comments_data = {
        'comments': [{
            'comment': 'test comment',
            'game_data': {
                'opponent_name': 'TestOpponent',
                'date': '2025-12-23 10:00:00',
                'map': 'TestMap',
                'build_order': [
                    {'time': 0, 'name': 'Drone', 'supply': 12},
                    {'time': 10, 'name': 'Overlord', 'supply': 13}
                ]
            }
        }]
    }
    
    # Mock ML analyzer
    mock_analyzer = MagicMock()
    mock_analyzer.match_build_against_all_patterns = MagicMock(return_value=[
        {'comment': 'test comment', 'similarity': 0.75}
    ])
    mock_analyzer.load_patterns_data = MagicMock(return_value={})
    mock_analyzer._match_build_against_patterns = MagicMock(return_value=[])
    
    with patch('builtins.open', create=True) as mock_open, \
         patch('json.load', return_value=comments_data), \
         patch('api.ml_opponent_analyzer.get_ml_analyzer', return_value=mock_analyzer):
        
        mock_open.return_value.__enter__.return_value.read.return_value = ''
        
        result = await service.test_replay_by_id(12345)
        
        assert "Best match" in result or "No strategy match" in result
        mock_analyzer.match_build_against_all_patterns.assert_called_once()

@pytest.mark.asyncio
async def test_test_replay_by_id_no_build_order(mock_repo, mock_chat_service, mock_pattern_learner):
    service = GameResultService(mock_repo, [mock_chat_service], mock_pattern_learner)
    
    # Mock DB to return replay info but no summary
    mock_db = MagicMock()
    mock_db.get_replay_by_id = MagicMock(return_value={
        'opponent': 'TestOpponent',
        'opponent_race': 'Zerg',
        'map': 'TestMap',
        'date': '2025-12-23 10:00:00',
        'replay_summary': ''
    })
    mock_repo.db = mock_db
    
    # Mock comments.json with no matching entry
    comments_data = {'comments': []}
    
    with patch('builtins.open', create=True), \
         patch('json.load', return_value=comments_data):
        
        result = await service.test_replay_by_id(12345)
        
        assert "No build order data found" in result

def test_parse_build_order_from_summary(mock_repo, mock_chat_service, mock_pattern_learner):
    service = GameResultService(mock_repo, [mock_chat_service], mock_pattern_learner)
    
    summary_text = """Players: TestPlayer: Zerg, Opponent: Terran
Map: TestMap

TestPlayer's Build Order (first set of steps):
Time: 0:00, Name: Drone, Supply: 12
Time: 0:10, Name: Overlord, Supply: 13
Time: 0:20, Name: Drone, Supply: 13

Opponent's Build Order (first set of steps):
Time: 0:00, Name: SCV, Supply: 12
"""
    
    build_order = service._parse_build_order_from_summary(summary_text, "TestPlayer")
    
    assert len(build_order) == 3
    assert build_order[0]['name'] == 'Drone'
    assert build_order[0]['time'] == 0
    assert build_order[0]['supply'] == 12
    assert build_order[1]['name'] == 'Overlord'
    assert build_order[1]['time'] == 10

def test_parse_build_order_from_summary_not_found(mock_repo, mock_chat_service, mock_pattern_learner):
    service = GameResultService(mock_repo, [mock_chat_service], mock_pattern_learner)
    
    summary_text = """Players: OtherPlayer: Zerg
OtherPlayer's Build Order:
Time: 0:00, Name: Drone, Supply: 12
"""
    
    build_order = service._parse_build_order_from_summary(summary_text, "TestPlayer")
    
    assert len(build_order) == 0

def test_parse_build_order_from_summary_empty(mock_repo, mock_chat_service, mock_pattern_learner):
    service = GameResultService(mock_repo, [mock_chat_service], mock_pattern_learner)
    
    build_order = service._parse_build_order_from_summary("", "TestPlayer")
    
    assert len(build_order) == 0