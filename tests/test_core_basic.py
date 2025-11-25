import pytest
import asyncio
from core.bot import BotCore
from core.events import MessageEvent
from tests.mocks.all_mocks import MockChatService, MockGameStateProvider, MockLanguageModel

@pytest.mark.asyncio
async def test_bot_initialization():
    chat_service = MockChatService()
    game_provider = MockGameStateProvider()
    llm = MockLanguageModel()
    
    bot = BotCore(
        chat_services=[chat_service], 
        game_state_provider=game_provider, 
        llm=llm
    )
    
    assert bot.running is False
    assert "mock_chat" in bot.chat_services

@pytest.mark.asyncio
async def test_event_processing_loop():
    chat_service = MockChatService()
    game_provider = MockGameStateProvider()
    llm = MockLanguageModel()
    
    bot = BotCore([chat_service], game_provider, llm)
    
    # Create a task to run the bot
    bot_task = asyncio.create_task(bot.start())
    
    # Let it start
    await asyncio.sleep(0.1)
    assert bot.running is True
    
    # Stop the bot
    bot.stop()
    await bot_task

@pytest.mark.asyncio
async def test_message_event_handling():
    chat_service = MockChatService()
    game_provider = MockGameStateProvider()
    llm = MockLanguageModel()
    
    bot = BotCore([chat_service], game_provider, llm)
    
    # Since we haven't implemented handle_message logic yet in BotCore,
    # we just verify the event loop consumes the event without error.
    # In a real TDD step, we would assert a side effect (like a reply).
    
    event = MessageEvent(
        platform="mock_chat",
        author="test_user",
        content="Hello Bot",
        channel="general"
    )
    
    bot.add_event(event)
    
    # Run bot briefly to process event
    task = asyncio.create_task(bot.start())
    await asyncio.sleep(0.1)
    bot.stop()
    await task
    
    # Verify queue is empty (event consumed)
    assert bot.event_queue.empty()


