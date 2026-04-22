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


@pytest.mark.asyncio
async def test_preview_handler_with_replay_id(mock_opponent_analysis_service, mock_twitch_bot, mock_chat_service):
    from core.handlers.preview_handler import PreviewHandler

    mock_twitch_bot.db = MagicMock()
    mock_twitch_bot.db.get_replay_by_id = MagicMock(return_value={
        "opponent": "ReplayEnemy",
        "opponent_race": "Zerg",
        "streamer_race": "Terran",
        "map": "Dynasty LE",
    })

    handler = PreviewHandler(mock_opponent_analysis_service, mock_twitch_bot)
    context = CommandContext("please preview 25593", "channel1", config.PAGE, "twitch", mock_chat_service)

    with patch('asyncio.get_running_loop') as mock_loop:
        mock_loop.return_value.run_in_executor = AsyncMock(return_value=True)
        await handler.handle(context, "25593")

    mock_twitch_bot.db.get_replay_by_id.assert_called_once_with(25593)
    calls = mock_chat_service.send_message.call_args_list
    assert any("ReplayID 25593" in str(call) for call in calls)


@pytest.mark.asyncio
async def test_preview_handler_with_invalid_replay_id_arg(mock_opponent_analysis_service, mock_twitch_bot, mock_chat_service):
    from core.handlers.preview_handler import PreviewHandler

    handler = PreviewHandler(mock_opponent_analysis_service, mock_twitch_bot)
    context = CommandContext("please review foo", "channel1", config.PAGE, "twitch", mock_chat_service)
    await handler.handle(context, "foo")

    mock_chat_service.send_message.assert_called_with(
        "channel1",
        "Usage: please preview [ReplayID] (or please review [ReplayID])"
    )


@pytest.mark.asyncio
async def test_preview_handler_with_negative_offset(mock_opponent_analysis_service, mock_twitch_bot, mock_chat_service):
    from core.handlers.preview_handler import PreviewHandler

    handler = PreviewHandler(mock_opponent_analysis_service, mock_twitch_bot)
    context = CommandContext("please review -60", "channel1", config.PAGE, "twitch", mock_chat_service)
    with patch.object(handler, "_load_replay_data_n_games_ago", new=AsyncMock(return_value={
        "map": "ObserverMap LE",
        "players": {
            "1": {"name": "PlayerA", "race": "Terran"},
            "2": {"name": "PlayerB", "race": "Zerg"},
        },
    })):
        await handler.handle(context, "-60")

    calls = mock_chat_service.send_message.call_args_list
    assert any("from 60 game(s) ago" in str(call) for call in calls)


@pytest.mark.asyncio
async def test_preview_handler_with_zero_arg(mock_opponent_analysis_service, mock_twitch_bot, mock_chat_service):
    from core.handlers.preview_handler import PreviewHandler

    handler = PreviewHandler(mock_opponent_analysis_service, mock_twitch_bot)
    context = CommandContext("please review 0", "channel1", config.PAGE, "twitch", mock_chat_service)
    await handler.handle(context, "0")

    mock_chat_service.send_message.assert_called_with(
        "channel1",
        "Preview supports ReplayID (>0) or negative offset (<0). Example: please preview 25593 or please preview -3",
    )


def test_preview_handler_resolve_players_for_preview_uses_summary(mock_opponent_analysis_service, mock_twitch_bot):
    from core.handlers.preview_handler import PreviewHandler

    handler = PreviewHandler(mock_opponent_analysis_service, mock_twitch_bot)
    replay_info = {
        "opponent": "WrongLegacyName",
        "opponent_race": "Unknown",
        "streamer_race": "Unknown",
        "replay_summary": """Players: Jmpzisbad: Zerg, NuKLeO: Terran
Jmpzisbad's Build Order (first set of steps):
Time: 0:00, Name: Drone, Supply: 12
""",
    }

    opponent, opponent_race, streamer_race, versus_name = handler._resolve_players_for_preview(replay_info)
    assert opponent == "Jmpzisbad"
    assert opponent_race == "Zerg"
    assert streamer_race == "Terran"
    assert versus_name == "NuKLeO"

