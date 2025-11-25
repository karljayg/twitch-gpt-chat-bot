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
    return service

@pytest.mark.asyncio
async def test_comment_handler_success(mock_repo, mock_learner, mock_chat_service):
    from core.handlers.comment_handler import CommentHandler
    
    handler = CommentHandler(mock_repo, mock_learner)
    context = CommandContext("player comment rush", "channel1", "user1", "twitch", mock_chat_service)
    
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
