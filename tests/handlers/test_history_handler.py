import pytest
from unittest.mock import MagicMock, AsyncMock
from core.command_service import CommandContext

@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.get_player_records = AsyncMock(return_value=["Player1 vs Opponent, Win-Loss"])
    return repo

@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.generate_response = AsyncMock(return_value="History Summary")
    return llm

@pytest.fixture
def mock_chat():
    chat = MagicMock()
    chat.send_message = AsyncMock()
    return chat

@pytest.mark.asyncio
async def test_history_handler(mock_repo, mock_llm, mock_chat):
    from core.handlers.history_handler import HistoryHandler
    
    handler = HistoryHandler(mock_repo, mock_llm)
    context = CommandContext("history Player1", "channel", "user", "twitch", mock_chat)
    
    await handler.handle(context, "Player1")
    
    mock_repo.get_player_records.assert_called_with("Player1")
    mock_llm.generate_response.assert_called()
    mock_chat.send_message.assert_called()

@pytest.mark.asyncio
async def test_history_handler_no_records(mock_repo, mock_llm, mock_chat):
    from core.handlers.history_handler import HistoryHandler
    
    mock_repo.get_player_records.return_value = []
    handler = HistoryHandler(mock_repo, mock_llm)
    context = CommandContext("history Unknown", "channel", "user", "twitch", mock_chat)
    
    await handler.handle(context, "Unknown")
    
    # Should still call LLM to generate "no records" message
    mock_llm.generate_response.assert_called()
    mock_chat.send_message.assert_called()


