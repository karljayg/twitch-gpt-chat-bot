import pytest
import asyncio
from core.bot import BotCore
from core.events import MessageEvent
from tests.mocks.all_mocks import MockChatService, MockGameStateProvider, MockLanguageModel

@pytest.mark.asyncio
async def test_bot_replies_to_chat():
    # ARRANGE
    chat_service = MockChatService("discord")
    game_provider = MockGameStateProvider()
    llm = MockLanguageModel()
    llm.set_response("hello", "Hello human!")

    bot = BotCore([chat_service], game_provider, llm)
    bot_task = asyncio.create_task(bot.start())

    # ACT
    # Simulate incoming user message "hello"
    event = MessageEvent(
        platform="discord",
        author="user1",
        content="hello bot",
        channel="general"
    )
    bot.add_event(event)

    # Allow time for processing
    await asyncio.sleep(0.1)

    # ASSERT
    # Verify the bot sent a reply via the chat service
    assert len(chat_service.sent_messages) == 1
    reply = chat_service.sent_messages[0]
    assert reply["channel"] == "general"
    assert reply["message"] == "Hello human!"

    # CLEANUP
    bot.stop()
    await bot_task

@pytest.mark.asyncio
async def test_bot_ignores_own_messages():
    # ARRANGE
    chat_service = MockChatService("discord")
    game_provider = MockGameStateProvider()
    llm = MockLanguageModel()
    
    bot = BotCore([chat_service], game_provider, llm)
    bot_task = asyncio.create_task(bot.start())
    
    # ACT
    # Simulate message FROM the bot itself (should be ignored)
    event = MessageEvent(
        platform="discord",
        author="MyBotName", # In real app, this would be config.USERNAME
        content="I am talking",
        channel="general"
    )
    # We need a way to tell the bot its own name. For now, let's assume hardcoded or config.
    # We will update BotCore to accept a bot_name.
    bot.bot_name = "MyBotName" 
    
    bot.add_event(event)
    await asyncio.sleep(0.1)
    
    # ASSERT
    assert len(chat_service.sent_messages) == 0
    
    bot.stop()
    await bot_task
