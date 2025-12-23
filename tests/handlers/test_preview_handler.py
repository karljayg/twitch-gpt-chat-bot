import pytest
from unittest.mock import MagicMock, AsyncMock, patch, mock_open
import json
from core.command_service import CommandContext
import settings.config as config

@pytest.fixture
def mock_opponent_analysis_service():
    service = MagicMock()
    service.analyze_opponent = MagicMock(return_value=True)
    return service

@pytest.fixture
def mock_twitch_bot():
    bot = MagicMock()
    return bot

@pytest.fixture
def mock_chat_service():
    service = MagicMock()
    service.send_message = AsyncMock()
    return service

@pytest.fixture
def sample_replay_data():
    return {
        'map': 'TestMap',
        'players': {
            '1': {'name': 'KJ', 'race': 'Terran'},
            '2': {'name': 'Opponent', 'race': 'Zerg'}
        }
    }

@pytest.mark.asyncio
async def test_preview_handler_success(mock_opponent_analysis_service, mock_twitch_bot, 
                                       mock_chat_service, sample_replay_data):
    from core.handlers.preview_handler import PreviewHandler
    
    handler = PreviewHandler(mock_opponent_analysis_service, mock_twitch_bot)
    context = CommandContext("please preview", "channel1", config.PAGE, "twitch", mock_chat_service)
    
    # Mock file loading
    with patch('os.path.exists', return_value=True), \
         patch('builtins.open', mock_open(read_data=json.dumps(sample_replay_data))), \
         patch('asyncio.get_running_loop') as mock_loop:
        
        mock_executor = MagicMock()
        mock_loop.return_value.run_in_executor = AsyncMock(return_value=True)
        
        await handler.handle(context, "")
        
        # Verify preview message sent
        mock_chat_service.send_message.assert_called()
        calls = mock_chat_service.send_message.call_args_list
        assert any("Previewing opponent analysis" in str(call) for call in calls)

@pytest.mark.asyncio
async def test_preview_handler_not_broadcaster(mock_opponent_analysis_service, mock_twitch_bot,
                                               mock_chat_service):
    from core.handlers.preview_handler import PreviewHandler
    
    handler = PreviewHandler(mock_opponent_analysis_service, mock_twitch_bot)
    context = CommandContext("please preview", "channel1", "random_user", "twitch", mock_chat_service)
    
    await handler.handle(context, "")
    
    # Should not send any messages
    mock_chat_service.send_message.assert_not_called()

@pytest.mark.asyncio
async def test_preview_handler_no_replay_data(mock_opponent_analysis_service, mock_twitch_bot,
                                               mock_chat_service):
    from core.handlers.preview_handler import PreviewHandler
    
    handler = PreviewHandler(mock_opponent_analysis_service, mock_twitch_bot)
    context = CommandContext("please preview", "channel1", config.PAGE, "twitch", mock_chat_service)
    
    with patch('os.path.exists', return_value=False):
        await handler.handle(context, "")
        
        mock_chat_service.send_message.assert_called_with(
            "channel1",
            "Preview failed - no recent replay data found. Play a game or run 'please retry' first."
        )

@pytest.mark.asyncio
async def test_preview_handler_no_opponent_info(mock_opponent_analysis_service, mock_twitch_bot,
                                                mock_chat_service):
    from core.handlers.preview_handler import PreviewHandler
    
    handler = PreviewHandler(mock_opponent_analysis_service, mock_twitch_bot)
    context = CommandContext("please preview", "channel1", config.PAGE, "twitch", mock_chat_service)
    
    # Replay data with no players
    bad_data = {'map': 'TestMap', 'players': {}}
    
    with patch('os.path.exists', return_value=True), \
         patch('builtins.open', mock_open(read_data=json.dumps(bad_data))):
        
        await handler.handle(context, "")
        
        mock_chat_service.send_message.assert_called_with(
            "channel1",
            "Preview failed - couldn't identify opponent from replay data."
        )

