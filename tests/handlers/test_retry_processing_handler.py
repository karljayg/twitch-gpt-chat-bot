import pytest
from unittest.mock import AsyncMock, MagicMock

import settings.config as config
from core.command_service import CommandContext
from core.handlers.retry_processing_handler import RetryProcessingHandler


@pytest.fixture
def mock_game_result_service():
    svc = MagicMock()
    svc.retry_with_reference = AsyncMock(return_value=(True, "Retried latest replay."))
    return svc


@pytest.fixture
def mock_chat_service():
    svc = MagicMock()
    svc.send_message = AsyncMock()
    return svc


@pytest.mark.asyncio
async def test_retry_no_arg_calls_latest(mock_game_result_service, mock_chat_service):
    game_result_service = mock_game_result_service
    chat_service = mock_chat_service
    h = RetryProcessingHandler(game_result_service)
    ctx = CommandContext("please retry", "chan", config.PAGE, "twitch", chat_service)

    await h.handle(ctx, "")

    game_result_service.retry_with_reference.assert_called_once_with(None)
    chat_service.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_retry_positive_id(mock_game_result_service, mock_chat_service):
    game_result_service = mock_game_result_service
    chat_service = mock_chat_service
    h = RetryProcessingHandler(game_result_service)
    ctx = CommandContext("please retry 24943", "chan", config.PAGE, "twitch", chat_service)

    await h.handle(ctx, "24943")

    game_result_service.retry_with_reference.assert_called_once_with(24943)


@pytest.mark.asyncio
async def test_retry_negative_offset(mock_game_result_service, mock_chat_service):
    game_result_service = mock_game_result_service
    chat_service = mock_chat_service
    h = RetryProcessingHandler(game_result_service)
    ctx = CommandContext("please retry -3", "chan", config.PAGE, "twitch", chat_service)

    await h.handle(ctx, "-3")

    game_result_service.retry_with_reference.assert_called_once_with(-3)


@pytest.mark.asyncio
async def test_retry_invalid_arg_shows_usage(mock_game_result_service, mock_chat_service):
    game_result_service = mock_game_result_service
    chat_service = mock_chat_service
    h = RetryProcessingHandler(game_result_service)
    ctx = CommandContext("please retry foo", "chan", config.PAGE, "twitch", chat_service)

    await h.handle(ctx, "foo")

    game_result_service.retry_with_reference.assert_not_called()
    sent = chat_service.send_message.call_args[0][1]
    assert "Usage: please retry" in sent

