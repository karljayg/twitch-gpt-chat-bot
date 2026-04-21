import pytest
from unittest.mock import MagicMock, AsyncMock
from core.command_service import CommandContext
from core.interfaces import IReplayRepository

@pytest.fixture
def mock_repo():
    repo = MagicMock(spec=IReplayRepository)
    repo.get_latest_replay = AsyncMock(return_value={
        'opponent': 'Opponent', 'map': 'Map', 'date': '2025-01-01', 
        'result': 'Victory', 'duration': '10m'
    })
    repo.update_comment = AsyncMock(return_value=True)
    return repo

@pytest.fixture
def mock_learner():
    learner = MagicMock()
    return learner

@pytest.fixture
def mock_chat_service():
    service = MagicMock()
    service.send_message = AsyncMock()
    # Mock twitch_bot with no pattern_learning_context (normal case)
    service.twitch_bot = None
    return service

@pytest.mark.asyncio
async def test_comment_handler_success(mock_repo, mock_learner, mock_chat_service):
    from core.handlers.comment_handler import CommentHandler
    import time
    
    handler = CommentHandler(mock_repo, mock_learner)
    context = CommandContext("player comment rush", "channel1", "user1", "twitch", mock_chat_service)
    
    # Ensure mock_learner has the expected methods
    mock_learner._process_new_comment = MagicMock()
    mock_learner.save_patterns_to_file = MagicMock()
    
    await handler.handle(context, "rush")
    
    mock_repo.update_comment.assert_called_with("rush")
    mock_learner._process_new_comment.assert_called()
    mock_chat_service.send_message.assert_called()
    
@pytest.mark.asyncio
async def test_comment_handler_no_replay(mock_repo, mock_learner, mock_chat_service):
    from core.handlers.comment_handler import CommentHandler
    
    mock_repo.get_latest_replay.return_value = None
    
    handler = CommentHandler(mock_repo, mock_learner)
    context = CommandContext("player comment rush", "channel1", "user1", "twitch", mock_chat_service)
    
    await handler.handle(context, "rush")
    
    mock_chat_service.send_message.assert_called_with("channel1", "No replays found in database - please play a game first")


@pytest.mark.asyncio
async def test_comment_handler_uses_target_replay_from_pattern_context(mock_repo, mock_learner, mock_chat_service):
    from core.handlers.comment_handler import CommentHandler
    import time

    mock_repo.db = MagicMock()
    mock_repo.db.get_replay_by_id = MagicMock(return_value={
        "replay_id": 25440,
        "opponent": "SirMalagant",
        "map": "Pylon LE",
        "date": "2026-03-27 23:50:54",
        "result": "Observed",
        "duration": "12m",
        "existing_comment": None,
    })
    mock_repo.db.update_player_comments_by_replay_id = MagicMock(return_value=True)

    mock_chat_service.twitch_bot = MagicMock()
    mock_chat_service.twitch_bot.pattern_learning_context = {
        "timestamp": time.time(),
        "game_data": {"replay_id": 25440},
    }

    handler = CommentHandler(mock_repo, mock_learner)
    context = CommandContext("player comment nexus cyber to adept twilight robo", "channel1", "user1", "twitch", mock_chat_service)
    await handler.handle(context, "nexus cyber to adept twilight robo")

    mock_repo.db.get_replay_by_id.assert_called_once_with(25440)
    mock_repo.db.update_player_comments_by_replay_id.assert_called_once()


@pytest.mark.asyncio
async def test_comment_handler_explicit_replay_id_prefix(mock_repo, mock_learner, mock_chat_service):
    from core.handlers.comment_handler import CommentHandler

    mock_repo.db = MagicMock()
    mock_repo.db.get_replay_by_id = MagicMock(
        return_value={
            "replay_id": 25456,
            "opponent": "X",
            "map": "M",
            "date": "2026-01-01 00:00:00",
            "result": "Win",
            "duration": "10m",
            "existing_comment": None,
        }
    )
    mock_repo.db.update_player_comments_by_replay_id = MagicMock(return_value=True)

    handler = CommentHandler(mock_repo, mock_learner)
    mock_learner._process_new_comment = MagicMock()
    mock_learner.save_patterns_to_file = MagicMock()

    context = CommandContext("player comment 25456 note", "ch", "u1", "twitch", mock_chat_service)
    await handler.handle(context, "25456 note")

    mock_repo.db.get_replay_by_id.assert_called_once_with(25456)
    mock_repo.db.update_player_comments_by_replay_id.assert_called_once_with(25456, "note")


@pytest.mark.asyncio
async def test_comment_handler_negative_offset_prefix(mock_repo, mock_learner, mock_chat_service):
    from core.handlers.comment_handler import CommentHandler

    mock_repo.db = MagicMock()
    mock_repo.db.get_replay_by_recency_offset = MagicMock(
        return_value={
            "replay_id": 9001,
            "opponent": "Y",
            "map": "M2",
            "date": "2026-01-02 00:00:00",
            "result": "Lose",
            "duration": "9m",
            "existing_comment": None,
        }
    )
    mock_repo.db.update_player_comments_by_replay_id = MagicMock(return_value=True)

    handler = CommentHandler(mock_repo, mock_learner)
    mock_learner._process_new_comment = MagicMock()
    mock_learner.save_patterns_to_file = MagicMock()

    context = CommandContext("player comment -2 zerg", "ch", "u1", "twitch", mock_chat_service)
    await handler.handle(context, "-2 zerg")

    mock_repo.db.get_replay_by_recency_offset.assert_called_once_with(2)
    mock_repo.db.update_player_comments_by_replay_id.assert_called_once_with(9001, "zerg")
