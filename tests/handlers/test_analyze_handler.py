import pytest
from unittest.mock import MagicMock, AsyncMock
from core.command_service import CommandContext

@pytest.fixture
def mock_analysis_service():
    service = MagicMock()
    service.analyze_opponent = AsyncMock(return_value={
        "play_style": "Aggressive",
        "win_rate": "55%",
        "main_race": "Zerg"
    })
    return service

@pytest.fixture
def mock_chat_service():
    service = MagicMock()
    service.send_message = AsyncMock()
    return service

@pytest.mark.asyncio
async def test_analyze_handler_success(mock_analysis_service, mock_chat_service):
    from core.handlers.analyze_handler import AnalyzeHandler
    
    handler = AnalyzeHandler(mock_analysis_service)
    context = CommandContext("analyze Player1", "channel1", "user1", "twitch", mock_chat_service)
    
    await handler.handle(context, "Player1")
    
    mock_analysis_service.analyze_opponent.assert_called_with("Player1", "Unknown")
    mock_chat_service.send_message.assert_called()

@pytest.mark.asyncio
async def test_analyze_handler_with_race(mock_analysis_service, mock_chat_service):
    from core.handlers.analyze_handler import AnalyzeHandler
    
    handler = AnalyzeHandler(mock_analysis_service)
    context = CommandContext("analyze Player1 Zerg", "channel1", "user1", "twitch", mock_chat_service)
    
    await handler.handle(context, "Player1 Zerg")
    
    mock_analysis_service.analyze_opponent.assert_called_with("Player1", "Zerg")

@pytest.mark.asyncio
async def test_analyze_handler_no_results(mock_analysis_service, mock_chat_service):
    from core.handlers.analyze_handler import AnalyzeHandler
    
    mock_analysis_service.analyze_opponent.return_value = None
    handler = AnalyzeHandler(mock_analysis_service)
    context = CommandContext("analyze Unknown", "channel1", "user1", "twitch", mock_chat_service)
    
    await handler.handle(context, "Unknown")
    
    mock_chat_service.send_message.assert_called_with("channel1", "Could not analyze opponent Unknown.")


