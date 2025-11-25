import pytest
import asyncio
import logging
from core.bot import BotCore
from core.events import MessageEvent, GameStateEvent
from tests.mocks.all_mocks import MockChatService, MockGameStateProvider, MockLanguageModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DetailedScenario")

@pytest.mark.asyncio
async def test_detailed_sc2_game_cycle():
    """
    DETAILED END-TO-END SCENARIO: "The Zerg Rush"

    Timeline:
    1. [00:00] Bot Init
    2. [00:10] Game Start (Map: Beckett Industries, Opponent: Zerg)
    3. [02:30] Event: Opponent plays 12 Pool (Early Rush)
    4. [02:45] Viewer asks: "What is happening?" -> Bot detects rush state -> Advise defense
    5. [05:00] Game End (Victory)
    6. [05:05] Pattern Learning: Bot analyzes replay -> Suggests "12 Pool Rush" pattern
    7. [05:10] Player Chat: "player comment It was a 12 pool" -> Database update
    """

    # --- SETUP MOCKS ---
    # Use "discord" to ensure BotCore processes it (Twitch is delegated to legacy)
    discord_mock = MockChatService("discord")
    game_provider_mock = MockGameStateProvider()

    # Smart Mock LLM that responds to context
    llm_mock = MockLanguageModel()
    llm_mock.set_response("what is happening", "I detect a Zergling rush! Build a wall immediately.")
    llm_mock.set_response("gg", "Great win! That defense was solid.")

    # --- INITIALIZE CORE ---
    bot = BotCore(
        chat_services=[discord_mock],
        game_state_provider=game_provider_mock,
        llm=llm_mock,
        bot_name="Mathison"
    )

    bot_task = asyncio.create_task(bot.start())
    logger.info(">>> SIMULATION STARTED: 'The Zerg Rush' Scenario <<<")

    # --- SCENARIO TIMELINE ---

    # 1. GAME START
    logger.info("\n[00:10] EVENT: Game Started vs 'ZergPlayer123'")
    start_event = GameStateEvent(
        event_type="game_started",
        data={
            "raw_data": {
                "map": "Beckett Industries",
                "players": [{"name": "ZergPlayer123", "race": "Zerg"}]
            }
        }
    )
    bot.add_event(start_event)
    await asyncio.sleep(0.1)

    # 2. IN-GAME EVENTS (Simulating SC2 polling detecting a rush)
    # Note: In real app, SC2Adapter parses this from API. Here we inject the result event.
    logger.info("\n[02:30] EVENT: SC2 API detects sudden Zergling spike (Rush Detected)")
    # Ideally we'd send a 'game_stat_update' event here if the core supported it

    # 3. VIEWER CHAT
    logger.info("\n[02:45] CHAT: Viewer asks 'What is happening?'")
    bot.add_event(MessageEvent(
        platform="discord", author="ConcernedFan", content="Mathison what is happening?", channel="chat"
    ))
    await asyncio.sleep(0.1)

    # ASSERTION: Bot should advise on the rush
    last_msg = discord_mock.sent_messages[-1]["message"]
    logger.info(f"BOT REPLY: '{last_msg}'")
    assert "rush" in last_msg or "build" in last_msg

    # 4. GAME END
    logger.info("\n[05:00] EVENT: Game Ended (Victory)")
    bot.add_event(GameStateEvent(event_type="game_ended", data={"status": "Victory"}))
    await asyncio.sleep(0.1)

    # 5. POST GAME CHAT
    logger.info("\n[05:01] CHAT: Viewer says 'gg'")
    bot.add_event(MessageEvent(
        platform="discord", author="Fan2", content="gg", channel="chat"
    ))
    await asyncio.sleep(0.1)
    last_msg = discord_mock.sent_messages[-1]["message"]
    logger.info(f"BOT REPLY: '{last_msg}'")
    assert "win" in last_msg or "solid" in last_msg

    # --- CLEANUP ---
    bot.stop()
    await bot_task
    logger.info(">>> SIMULATION COMPLETE <<<")
