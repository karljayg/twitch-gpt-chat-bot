import pytest
from unittest.mock import MagicMock, AsyncMock
from adapters.discord_adapter import DiscordAdapter
from core.events import MessageEvent

@pytest.fixture
def mock_bot_core():
    core = MagicMock()
    core.add_event = MagicMock()
    return core

@pytest.fixture
def mock_discord_bot():
    bot = MagicMock()
    bot.channel_id = "12345"
    bot.send_message_to_discord = AsyncMock()
    bot.get_channel = MagicMock()
    return bot

@pytest.mark.asyncio
async def test_send_message_generic(mock_bot_core, mock_discord_bot):
    adapter = DiscordAdapter(mock_bot_core, mock_discord_bot)
    
    # Test sending to "discord" (generic)
    await adapter.send_message("discord", "Hello")
    mock_discord_bot.send_message_to_discord.assert_called_with("Hello")
    
    # Test sending to matching channel ID
    await adapter.send_message("12345", "Hello 2")
    mock_discord_bot.send_message_to_discord.assert_called_with("Hello 2")

@pytest.mark.asyncio
async def test_send_message_specific_channel(mock_bot_core, mock_discord_bot):
    adapter = DiscordAdapter(mock_bot_core, mock_discord_bot)
    
    mock_channel = AsyncMock()
    mock_discord_bot.get_channel.return_value = mock_channel
    
    # Sending to a numeric ID that isn't the default one
    await adapter.send_message("98765", "Hello specific")
    
    mock_discord_bot.get_channel.assert_called_with(98765)
    mock_channel.send.assert_called_with("Hello specific")

@pytest.mark.asyncio
async def test_on_message(mock_bot_core, mock_discord_bot):
    adapter = DiscordAdapter(mock_bot_core, mock_discord_bot)
    
    adapter.on_message("User1", "Hi", "general")
    
    mock_bot_core.add_event.assert_called()
    args, _ = mock_bot_core.add_event.call_args
    event = args[0]
    assert isinstance(event, MessageEvent)
    assert event.platform == "discord"
    assert event.author == "User1"
    assert event.content == "Hi"


