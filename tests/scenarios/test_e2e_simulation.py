import pytest
import asyncio
import logging
from core.bot import BotCore
from core.events import MessageEvent, GameStateEvent
from tests.mocks.all_mocks import MockChatService, MockGameStateProvider, MockLanguageModel

# Configure logging for the test to see output
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("ScenarioTest")

@pytest.mark.asyncio
async def test_full_game_session_simulation():
    """
    END-TO-END SIMULATION TEST
    
    This test simulates a complete lifecycle of the bot:
    1. Initialization
    2. SC2 Game Start
    3. Chat interaction during game
    4. SC2 Game End
    5. Pattern Learning Trigger
    """
    
    # --- SETUP MOCKS ---
    # Use "discord" platform to bypass legacy fallback logic in BotCore
    discord_mock = MockChatService("discord")
    game_provider_mock = MockGameStateProvider()
    llm_mock = MockLanguageModel()
    llm_mock.set_response("strategy", "You should build more workers.")
    llm_mock.set_response("gg", "Good game!")
    llm_mock.set_response("hello", "Hello! I am Mathison.")
    llm_mock.set_response("The game has started", "GLHF! Hype!")
    
    # --- INITIALIZE CORE ---
    bot = BotCore(
        chat_services=[discord_mock], 
        game_state_provider=game_provider_mock, 
        llm=llm_mock,
        bot_name="Mathison"
    )
    
    bot_task = asyncio.create_task(bot.start())
    logger.info("Bot started in simulation mode")
    
    # STEP 1: CHAT BEFORE GAME
    logger.info("--- STEP 1: Chat Before Game ---")
    bot.add_event(MessageEvent(
        platform="discord", author="Viewer1", content="hello bot", channel="chat"
    ))
    await asyncio.sleep(0.1)
    
    assert len(discord_mock.sent_messages) == 1
    assert discord_mock.sent_messages[-1]["message"] == "Hello! I am Mathison."
    
    # STEP 2: GAME START
    logger.info("--- STEP 2: Game Start ---")
    game_start_event = GameStateEvent(
        event_type="game_started",
        data={"raw_data": {"players": [{"name": "Opponent", "race": "Zerg"}]}}
    )
    bot.add_event(game_start_event)
    await asyncio.sleep(0.1)
    
    # VERIFY INTRO MESSAGE
    # The bot should now send a message on game start
    assert len(discord_mock.sent_messages) == 2
    logger.info(f"Intro message: {discord_mock.sent_messages[-1]['message']}")
    
    # STEP 3: CHAT DURING GAME
    logger.info("--- STEP 3: Chat During Game ---")
    bot.add_event(MessageEvent(
        platform="discord", author="Viewer2", content="what is the strategy?", channel="chat"
    ))
    await asyncio.sleep(0.1)
    
    assert len(discord_mock.sent_messages) == 3
    assert discord_mock.sent_messages[-1]["message"] == "You should build more workers."
    
    # STEP 4: GAME END
    logger.info("--- STEP 4: Game End ---")
    game_end_event = GameStateEvent(
        event_type="game_ended",
        data={"status": "Victory"}
    )
    bot.add_event(game_end_event)
    await asyncio.sleep(0.1)
    
    # STEP 5: POST-GAME CHAT
    logger.info("--- STEP 5: Post-Game Chat ---")
    bot.add_event(MessageEvent(
        platform="discord", author="Viewer1", content="gg", channel="chat"
    ))
    await asyncio.sleep(0.1)
    
    assert len(discord_mock.sent_messages) == 4
    assert discord_mock.sent_messages[-1]["message"] == "Good game!"
    
    # --- CLEANUP ---
    bot.stop()
    await bot_task
    logger.info("Simulation complete")
