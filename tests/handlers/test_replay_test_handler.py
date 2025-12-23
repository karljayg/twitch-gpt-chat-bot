import pytest
from unittest.mock import MagicMock, AsyncMock
from core.command_service import CommandContext
import settings.config as config

@pytest.fixture
def mock_game_result_service():
    service = MagicMock()
    service.test_replay_by_id = AsyncMock(return_value="Replay 12345 vs Opponent: Best match 'rush' at 75%")
    return service

@pytest.fixture
def mock_chat_service():
    service = MagicMock()
    service.send_message = AsyncMock()
    return service

@pytest.mark.asyncio
async def test_replay_test_handler_success(mock_game_result_service, mock_chat_service):
    from core.handlers.replay_test_handler import ReplayTestHandler
    
    handler = ReplayTestHandler(mock_game_result_service)
    context = CommandContext("please replay 12345", "channel1", config.PAGE, "twitch", mock_chat_service)
    
    await handler.handle(context, "12345")
    
    mock_game_result_service.test_replay_by_id.assert_called_once_with(12345)
    mock_chat_service.send_message.assert_called_once_with(
        "channel1",
        "Replay 12345 vs Opponent: Best match 'rush' at 75%"
    )

@pytest.mark.asyncio
async def test_replay_test_handler_not_broadcaster(mock_game_result_service, mock_chat_service):
    from core.handlers.replay_test_handler import ReplayTestHandler
    
    handler = ReplayTestHandler(mock_game_result_service)
    context = CommandContext("please replay 12345", "channel1", "random_user", "twitch", mock_chat_service)
    
    await handler.handle(context, "12345")
    
    # Should not call test_replay_by_id
    mock_game_result_service.test_replay_by_id.assert_not_called()
    mock_chat_service.send_message.assert_not_called()

@pytest.mark.asyncio
async def test_replay_test_handler_no_args(mock_game_result_service, mock_chat_service):
    from core.handlers.replay_test_handler import ReplayTestHandler
    
    handler = ReplayTestHandler(mock_game_result_service)
    context = CommandContext("please replay", "channel1", config.PAGE, "twitch", mock_chat_service)
    
    await handler.handle(context, "")
    
    mock_chat_service.send_message.assert_called_with(
        "channel1",
        "Usage: please replay <replayID> - e.g. 'please replay 12345'"
    )
    mock_game_result_service.test_replay_by_id.assert_not_called()

@pytest.mark.asyncio
async def test_replay_test_handler_invalid_id(mock_game_result_service, mock_chat_service):
    from core.handlers.replay_test_handler import ReplayTestHandler
    
    handler = ReplayTestHandler(mock_game_result_service)
    context = CommandContext("please replay abc", "channel1", config.PAGE, "twitch", mock_chat_service)
    
    await handler.handle(context, "abc")
    
    mock_chat_service.send_message.assert_called_with(
        "channel1",
        "Invalid replay ID: 'abc'. Must be a number."
    )
    mock_game_result_service.test_replay_by_id.assert_not_called()

@pytest.mark.asyncio
async def test_replay_test_handler_error(mock_game_result_service, mock_chat_service):
    from core.handlers.replay_test_handler import ReplayTestHandler
    
    mock_game_result_service.test_replay_by_id = AsyncMock(side_effect=Exception("DB error"))
    
    handler = ReplayTestHandler(mock_game_result_service)
    context = CommandContext("please replay 12345", "channel1", config.PAGE, "twitch", mock_chat_service)
    
    await handler.handle(context, "12345")
    
    mock_chat_service.send_message.assert_called_with(
        "channel1",
        "Replay test failed: DB error"
    )

