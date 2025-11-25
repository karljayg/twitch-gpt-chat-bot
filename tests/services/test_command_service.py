import pytest
from unittest.mock import MagicMock, AsyncMock
from core.command_service import CommandService, CommandContext, ICommandHandler

class MockHandler(ICommandHandler):
    def __init__(self):
        self.handle_mock = AsyncMock()
        
    async def handle(self, context: CommandContext, args: str):
        await self.handle_mock(context, args)

@pytest.fixture
def mock_chat_service():
    service = MagicMock()
    service.send_message = AsyncMock()
    service.platform = "twitch"
    return service

@pytest.mark.asyncio
async def test_dispatch_wiki_command(mock_chat_service):
    service = CommandService([mock_chat_service])
    wiki_handler = MockHandler()
    service.register_handler("wiki", wiki_handler)
    
    # Test with arguments
    await service.handle_message("wiki zerglings", "channel1", "user1", "twitch")
    
    wiki_handler.handle_mock.assert_called_once()
    args = wiki_handler.handle_mock.call_args[0][1]
    assert args == "zerglings"

@pytest.mark.asyncio
async def test_dispatch_exact_command(mock_chat_service):
    service = CommandService([mock_chat_service])
    help_handler = MockHandler()
    service.register_handler("help", help_handler)
    
    # Test exact match no args
    await service.handle_message("help", "channel1", "user1", "twitch")
    
    help_handler.handle_mock.assert_called_once()
    args = help_handler.handle_mock.call_args[0][1]
    assert args == ""

@pytest.mark.asyncio
async def test_dispatch_player_comment(mock_chat_service):
    service = CommandService([mock_chat_service])
    comment_handler = MockHandler()
    service.register_handler("player comment", comment_handler)
    
    await service.handle_message("player comment this was a rush", "channel1", "user1", "twitch")
    
    comment_handler.handle_mock.assert_called_once()
    args = comment_handler.handle_mock.call_args[0][1]
    assert args == "this was a rush"

@pytest.mark.asyncio
async def test_no_partial_match(mock_chat_service):
    service = CommandService([mock_chat_service])
    win_handler = MockHandler()
    service.register_handler("win", win_handler)
    
    # Should NOT match "winter"
    result = await service.handle_message("winter is coming", "channel1", "user1", "twitch")
    
    assert result is False
    win_handler.handle_mock.assert_not_called()

@pytest.mark.asyncio
async def test_longest_match_wins(mock_chat_service):
    service = CommandService([mock_chat_service])
    player_handler = MockHandler()
    player_comment_handler = MockHandler()
    
    service.register_handler("player", player_handler)
    service.register_handler("player comment", player_comment_handler)
    
    # Should match "player comment" not just "player"
    await service.handle_message("player comment hello", "channel1", "user1", "twitch")
    
    player_comment_handler.handle_mock.assert_called_once()
    player_handler.handle_mock.assert_not_called()
