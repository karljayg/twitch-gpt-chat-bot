import pytest
from unittest.mock import MagicMock, AsyncMock
from core.command_service import CommandContext
from core.interfaces import ILanguageModel, IPlayerRepository

@pytest.fixture
def mock_repo():
    repo = MagicMock(spec=IPlayerRepository)
    repo.get_player_stats = AsyncMock(return_value="10 wins 5 losses")
    repo.get_matchup_stats = AsyncMock(return_value="PvP: 5-2")
    return repo

@pytest.fixture
def mock_llm():
    llm = MagicMock(spec=ILanguageModel)
    llm.generate_response = AsyncMock(return_value="Career: 10-5 (PvP 5-2)")
    return llm

@pytest.mark.asyncio
async def test_career_handler_success(mock_repo, mock_llm):
    from core.handlers.career_handler import CareerHandler
    
    mock_chat = MagicMock()
    mock_chat.send_message = AsyncMock()
    
    handler = CareerHandler(mock_repo, mock_llm)
    context = CommandContext("career Player1", "channel1", "user1", "twitch", mock_chat)
    
    await handler.handle(context, "Player1")
    
    mock_repo.get_player_stats.assert_called_with("Player1")
    mock_llm.generate_response.assert_called()
    mock_chat.send_message.assert_called_with("channel1", "Career: 10-5 (PvP 5-2)")

@pytest.mark.asyncio
async def test_career_handler_no_results(mock_repo, mock_llm):
    from core.handlers.career_handler import CareerHandler
    
    mock_repo.get_player_stats.return_value = None
    mock_chat = MagicMock()
    mock_chat.send_message = AsyncMock()
    
    handler = CareerHandler(mock_repo, mock_llm)
    context = CommandContext("career Unknown", "channel1", "user1", "twitch", mock_chat)
    
    await handler.handle(context, "Unknown")
    
    mock_chat.send_message.assert_called_with("channel1", "No records found for Unknown")
