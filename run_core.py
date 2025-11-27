import asyncio
import logging
import sys
import signal
import threading
from typing import List

# Configure logging - Initial setup (console only)
# File logging will be added after TwitchBot initializes its file handler
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Suppress noisy libraries
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

# Completely suppress Discord gateway shard messages (RESUME, RECONNECT, etc.)
class DiscordGatewayFilter(logging.Filter):
    def filter(self, record):
        # Suppress shard RESUME/RECONNECT messages
        if 'RESUMED session' in record.getMessage() or 'RECONNECT' in record.getMessage():
            return False
        return True

discord_gateway_logger = logging.getLogger('discord.gateway')
discord_gateway_logger.setLevel(logging.WARNING)
discord_gateway_logger.addFilter(DiscordGatewayFilter())

logger = logging.getLogger("RunCore")

# Import Core
from core.bot import BotCore
from core.interfaces import IChatService, IGameStateProvider, ILanguageModel
# Import Adapters
from adapters.twitch_adapter import TwitchAdapter
from adapters.discord_adapter import DiscordAdapter
from adapters.sc2_adapter import SC2Adapter
from adapters.openai_adapter import OpenAIAdapter

# Import New Services & Repositories
from core.repositories.sql_replay_repository import SqlReplayRepository
from core.repositories.sql_player_repository import SqlPlayerRepository
from core.audio_service import AudioService
from core.services.analysis_service import AnalysisService
from core.pattern_learning_service import PatternLearningService
from core.command_service import CommandService
from core.game_result_service import GameResultService

# Import Handlers
from core.handlers.wiki_handler import WikiHandler
from core.handlers.career_handler import CareerHandler
from core.handlers.comment_handler import CommentHandler
from core.handlers.analyze_handler import AnalyzeHandler
from core.handlers.history_handler import HistoryHandler
from core.handlers.fsl_handler import FSLHandler
from core.handlers.head_to_head_handler import HeadToHeadHandler
from core.handlers.retry_processing_handler import RetryProcessingHandler

# Import Legacy Bots & Utils
from api.twitch_bot import TwitchBot
from api.discord_bot import DiscordBot, start_discord_bot
from api.ml_opponent_analyzer import get_ml_analyzer
import settings.config as config
import api.text2speech as tts_module # Legacy TTS module

# Check for command-line arguments
if len(sys.argv) > 1:
    for arg in sys.argv[1:]:
        if "PLAYER_INTROS_ENABLED=" in arg:
            value = arg.split("=")[1].lower()
            config.PLAYER_INTROS_ENABLED = value == "true"
            print(f"PLAYER_INTROS_ENABLED set to: {config.PLAYER_INTROS_ENABLED}")

async def main():
    logger.info("Starting Mathison TDD Architecture...")

    # 1. Initialize Legacy Bots
    # Disable legacy monitor thread to avoid conflict with new SC2Adapter
    twitch_bot_legacy = TwitchBot(start_monitor=False)
    
    # Share the TwitchBot's file handler with all loggers
    # This ensures BotCore, SC2Adapter, etc. all log to the same file
    twitch_logger = logging.getLogger('api.twitch_bot')
    for handler in twitch_logger.handlers:
        if isinstance(handler, logging.FileHandler):
            # Add this file handler to the root logger
            root_logger = logging.getLogger()
            root_logger.addHandler(handler)
            logger.info(f"Shared file logging enabled: {handler.baseFilename}")
            break
    
    # Note: DiscordBot needs to be started via start_discord_bot or manual task
    discord_bot_legacy = DiscordBot(twitch_bot_legacy)

    # 2. Initialize Core & Adapters
    # Use Real OpenAI Adapter
    if not config.OPENAI_DISABLED:
        llm = OpenAIAdapter()
        logger.info("OpenAI Adapter enabled.")
    else:
        from tests.mocks.all_mocks import MockLanguageModel
        llm = MockLanguageModel()
        llm.set_response("hello", "OpenAI is disabled in config.")
        logger.warning("OpenAI disabled - using Mock LLM.")

    # 3. Initialize Services & Repositories
    
    # Repositories
    replay_repo = SqlReplayRepository(twitch_bot_legacy.db)
    player_repo = SqlPlayerRepository(twitch_bot_legacy.db)
    
    # Audio Service
    sound_player_instance = getattr(twitch_bot_legacy, 'sound_player', None)
    audio_service = AudioService(sound_player=sound_player_instance, tts_module=tts_module)
    if sound_player_instance:
        logger.info(f"AudioService initialized with sound_player: {type(sound_player_instance).__name__}")
    else:
        logger.warning("AudioService initialized WITHOUT sound_player (sounds will not play)")
    
    # Analysis Service
    try:
        analyzer_instance = get_ml_analyzer()
        analysis_service = AnalysisService(analyzer_instance, twitch_bot_legacy.db)
    except Exception as e:
        logger.warning(f"Could not initialize Analysis Service: {e}")
        analysis_service = None
    
    # Pattern Learning Service
    pattern_learning_service = PatternLearningService(
        llm=llm,
        pattern_learner=getattr(twitch_bot_legacy, 'pattern_learner', None)
    ) 
    
    # Create Core (initially without command service)
    from tests.mocks.all_mocks import MockGameStateProvider
    dummy_provider = MockGameStateProvider()
    
    bot_core = BotCore(
        chat_services=[], 
        game_state_provider=dummy_provider, 
        llm=llm,
        audio_service=audio_service
    )
    
    # Create Adapters
    twitch_adapter = TwitchAdapter(bot_core, twitch_bot_legacy)
    
    # Update Core
    bot_core.chat_services[twitch_adapter.get_platform_name()] = twitch_adapter

    # Register Adapter with Legacy Bot for Message Forwarding
    twitch_bot_legacy.set_message_handler(twitch_adapter.on_message)
    
    # Conditionally enable Discord
    discord_adapter = None
    if config.DISCORD_ENABLED and config.DISCORD_TOKEN:
        discord_adapter = DiscordAdapter(bot_core, discord_bot_legacy)
        bot_core.chat_services[discord_adapter.get_platform_name()] = discord_adapter
    
    # 4. Command Service & Handlers
    # Pass only active chat services
    active_adapters = [twitch_adapter]
    if discord_adapter:
        active_adapters.append(discord_adapter)
        
    command_service = CommandService(active_adapters)
    
    # Handlers
    wiki_handler = WikiHandler(llm)
    career_handler = CareerHandler(player_repo, llm)
    history_handler = HistoryHandler(player_repo, llm)
    fsl_handler = FSLHandler()
    head_to_head_handler = HeadToHeadHandler(player_repo, llm)
    
    # CommentHandler uses legacy pattern learner for now to maintain compatibility with file storage
    comment_handler = CommentHandler(replay_repo, getattr(twitch_bot_legacy, 'pattern_learner', None))
    
    # Register Handlers
    command_service.register_handler("wiki", wiki_handler)
    command_service.register_handler("career", career_handler)
    command_service.register_handler("history", history_handler)
    command_service.register_handler("player comment", comment_handler)
    command_service.register_handler("fsl_review", fsl_handler)
    command_service.register_handler("head to head", head_to_head_handler)
    
    if analysis_service:
        analyze_handler = AnalyzeHandler(analysis_service)
        command_service.register_handler("analyze", analyze_handler)
    
    # Inject CommandService into Core
    bot_core.command_service = command_service
    
    # 5. Game Result Service
    # Filter out Discord from game result announcements per user requirement (Twitch only for game stats)
    game_result_services = [s for s in active_adapters if s.get_platform_name() == "twitch"]
    
    game_result_service = GameResultService(
        replay_repo=replay_repo,
        chat_services=game_result_services, 
        pattern_learner=getattr(twitch_bot_legacy, 'pattern_learner', None)
    )
    
    # Register retry processing handler (must be after game_result_service is created)
    retry_handler = RetryProcessingHandler(game_result_service)
    command_service.register_handler("please retry", retry_handler)
    
    # SC2 Adapter with GameResultService
    sc2_adapter = SC2Adapter(bot_core, game_result_service)
    
    # Update Core
    bot_core.game_state = sc2_adapter
    
    # 6. Start Background Tasks
    tasks = []
    loop = asyncio.get_event_loop()
    
    # Setup signal handlers for graceful shutdown
    stop_event = asyncio.Event()
    
    def signal_handler():
        logger.info("Received shutdown signal")
        stop_event.set()
        
    if sys.platform != 'win32':
        loop.add_signal_handler(signal.SIGINT, signal_handler)
        loop.add_signal_handler(signal.SIGTERM, signal_handler)
    
    # A) Bot Core Event Loop
    tasks.append(asyncio.create_task(bot_core.start()))
    
    # B) SC2 Monitoring Loop (New Adapter)
    if config.ENABLE_SC2_MONITORING:
        tasks.append(asyncio.create_task(sc2_adapter.start_monitoring()))
    
    # C) Twitch Bot (Run in Daemon Thread)
    logger.info("Starting Twitch Bot (Daemon Thread)...")
    # We run this in a DAEMON thread so it doesn't block shutdown if it hangs
    twitch_thread = threading.Thread(target=twitch_bot_legacy.start, daemon=True)
    twitch_thread.start()
    # We don't need to append this to tasks as it's a thread, not an async task.
    # We will manage its shutdown via the 'die' command.
    
    # D) Discord Bot (Async)
    if config.DISCORD_ENABLED and config.DISCORD_TOKEN:
        logger.info("Starting Discord Bot...")
        try:
            import api.discord_bot
            api.discord_bot.discord_bot_instance = discord_bot_legacy
            
            discord_task = asyncio.create_task(discord_bot_legacy.start(config.DISCORD_TOKEN))
            tasks.append(discord_task)
        except Exception as e:
            logger.error(f"Failed to create Discord task: {e}")
    else:
        logger.info("Discord disabled or missing token.")

    logger.info(f"System running with {len(tasks)} active tasks. Press Ctrl+C to stop.")
    
    # Wait for stop event or tasks
    try:
        # Wait for either the stop event (signal) or all tasks to complete (unlikely)
        # Or catch KeyboardInterrupt if on Windows/no signal handler
        if sys.platform == 'win32':
            # On Windows, we poll/wait on tasks. Ctrl+C raises KeyboardInterrupt.
            await asyncio.gather(*tasks)
        else:
            await stop_event.wait()
            
    except asyncio.CancelledError:
        logger.info("Shutting down (Cancelled)...")
    except KeyboardInterrupt:
         logger.info("Shutting down (KeyboardInterrupt)...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        logger.info("Starting cleanup...")
        
        # 1. Signal Legacy Twitch Bot to stop
        # Since it's a daemon thread now, this is polite but not blocking
        twitch_bot_legacy.die() 
        
        # 2. Stop BotCore (stops event processing)
        bot_core.stop()
        
        # 3. Stop SC2 Adapter (stops monitoring loop)
        sc2_adapter.stop()
        
        # 4. Cleanly close Discord
        if config.DISCORD_ENABLED and not discord_bot_legacy.is_closed():
             try:
                await discord_bot_legacy.close()
             except Exception as e:
                 logger.error(f"Error closing Discord bot: {e}")

        # 5. Cancel all pending tasks
        pending = asyncio.all_tasks(loop)
        for task in pending:
            if not task.done() and task != asyncio.current_task():
                task.cancel()
        
        # Give tasks a moment to cancel
        await asyncio.sleep(0.5)
        
        logger.info("Cleanup complete.")

if __name__ == "__main__":
    try:
        # Windows-specific event loop policy to avoid "Event loop is closed" errors
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            
        asyncio.run(main())
    except KeyboardInterrupt:
        # Catch Ctrl+C at the top level if it bubbles up
        pass
