import asyncio
import logging
import queue
from typing import Dict, List, Optional, Any
from core.interfaces import IChatService, IGameStateProvider, ILanguageModel, IAudioService
from core.events import BaseEvent, MessageEvent, GameStateEvent
import settings.config as config

logger = logging.getLogger(__name__)

class BotCore:
    def __init__(self, 
                 chat_services: List[IChatService],
                 game_state_provider: IGameStateProvider,
                 llm: ILanguageModel,
                 bot_name: str = "bot",
                 command_service: Optional[Any] = None,
                 audio_service: Optional[IAudioService] = None): # Added audio_service
        self.chat_services = {s.get_platform_name(): s for s in chat_services}
        self.game_state = game_state_provider
        self.llm = llm
        self.bot_name = bot_name
        self.command_service = command_service
        self.audio_service = audio_service
        self.event_queue = queue.Queue()
        self.running = False
        
        # Internal State
        self.current_game_status = "Idle"
        
        # Log audio service status
        if self.audio_service:
            logger.debug(f"BotCore initialized with AudioService")
        else:
            logger.warning("BotCore initialized WITHOUT AudioService")
        
    def add_event(self, event: BaseEvent):
        """Add an event to the processing queue"""
        self.event_queue.put(event)
        
    async def start(self):
        """Start the bot processing loop"""
        self.running = True
        logger.info("BotCore started")
        while self.running:
            try:
                # Non-blocking get with timeout to allow checking self.running
                try:
                    event = self.event_queue.get_nowait()
                    await self.process_event(event)
                except queue.Empty:
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in BotCore loop: {e}")
                await asyncio.sleep(1)
                
    async def process_event(self, event: BaseEvent):
        """Process a single event"""
        event_type = type(event).__name__
        logger.info(f"Processing event: {event_type}")
        
        if isinstance(event, MessageEvent):
            await self.handle_message(event)
        elif isinstance(event, GameStateEvent):
            logger.info(f"GameStateEvent detected: {event.event_type}")
            await self.handle_game_state(event)
            
    async def handle_message(self, event: MessageEvent):
        # Ignore own messages
        if event.author == self.bot_name:
            return

        # 1. Try Command Service
        if self.command_service:
            try:
                handled = await self.command_service.handle_message(
                    event.content, event.channel, event.author, event.platform
                )
                if handled:
                    logger.info(f"Message handled by CommandService: {event.content}")
                    return
            except Exception as e:
                logger.error(f"Error in CommandService: {e}")

        # 2. Legacy Handling Fallback (Twitch)
        if event.platform == "twitch":
            # Legacy TwitchBot already processed this via on_pubmsg
            # No need to duplicate processing for general chat
            logger.debug(f"Twitch message from {event.author}: {event.content} (handled by legacy)")
            return
        
        # 3. For other platforms (Discord), use LLM to generate response (always respond)
        context = []
        if self.current_game_status == "InGame":
            context.append("Game is currently active.")
        
        try:
            response = await self.llm.generate_response(event.content, context=context)
            
            if response:
                service = self.chat_services.get(event.platform)
                if service:
                    await service.send_message(event.channel, response)
                else:
                    logger.warning(f"No chat service found for platform: {event.platform}")
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
        
    async def handle_game_state(self, event: GameStateEvent):
        logger.info(f"Game State Changed: {event.event_type}")
        
        if event.event_type == "game_started":
            self.current_game_status = "InGame"
            logger.info("Status set to InGame")
            
            # Sync conversation_mode with legacy TwitchBot
            twitch_service = self.chat_services.get('twitch')
            if twitch_service and hasattr(twitch_service, 'twitch_bot'):
                twitch_service.twitch_bot.conversation_mode = "in_game"
                logger.debug("Synced conversation_mode to 'in_game'")
            
            # Extract Game Info
            data = event.data or {}
            game_info = data.get('raw_data')
            
            # Determine Opponent
            opponent_name = "Unknown Opponent"
            opponent_race = "Unknown Race"
            
            if game_info:
                try:
                    if hasattr(game_info, 'players'):
                        for p in game_info.players:
                            opponent_name = p.get('name', 'Unknown')
                            opponent_race = p.get('race', 'Unknown')
                except Exception as e:
                    logger.error(f"Failed to parse game info for intro: {e}")

            # 1. Play Game Start Sound (Intro) - Do this first for immediate feedback
            if self.audio_service and config.PLAYER_INTROS_ENABLED:
                logger.info("Playing Game Start Intro Sound via AudioService")
                await self.audio_service.play_sound("start")

            # 2. Trigger Legacy Analysis (The "Head-to-Head" and "Previous History" message)
            # This was previously handled by api/game_event_utils/game_started_handler.py
            # We need to invoke that logic to get the rich detailed message the user wants.
            
            twitch_service = self.chat_services.get('twitch')
            if twitch_service and hasattr(twitch_service, 'twitch_bot'):
                logger.info("Invoking legacy game_started_handler for detailed analysis...")
                # We run this in executor because it's synchronous legacy code with DB calls
                loop = asyncio.get_running_loop()
                try:
                    from api.game_event_utils.game_started_handler import game_started
                    # We need to pass: self (twitch_bot), current_game, contextHistory, logger
                    # contextHistory is a global in twitch_bot.py, but we can access it via the bot instance if needed
                    # or pass a new list if it just needs a buffer.
                    # The legacy code uses `contextHistory` passed as argument.
                    
                    # Access global contextHistory from twitch_bot module if possible, or use bot's ref
                    import api.twitch_bot
                    ctx_hist = api.twitch_bot.contextHistory
                    
                    await loop.run_in_executor(
                        None,
                        game_started,
                        twitch_service.twitch_bot, # self
                        game_info,                 # current_game
                        ctx_hist,                  # contextHistory
                        logger                     # logger
                    )
                    logger.info("Legacy game start analysis completed.")
                except Exception as e:
                    logger.error(f"Error running legacy game start analysis: {e}")
            else:
                # Fallback if legacy bot not available (shouldn't happen in current hybrid mode)
                logger.warning("Legacy bot not available for game start analysis. Using simple fallback.")
                prompt = f"The game has started against {opponent_name} ({opponent_race}). Give a short, hype 1-sentence intro for the stream."
                intro_message = await self.llm.generate_response(prompt)
                if not intro_message:
                    intro_message = f"Game Started! GLHF vs {opponent_name} ({opponent_race})!"
                # Send to any available chat service (not just Twitch)
                for service in self.chat_services.values():
                    await service.send_message("chat", intro_message)
                    break  # Send to first available service
                
        elif event.event_type == "game_ended":
            self.current_game_status = "Idle"
            logger.info("Status set to Idle")
            
            # Sync conversation_mode with legacy TwitchBot
            twitch_service = self.chat_services.get('twitch')
            if twitch_service and hasattr(twitch_service, 'twitch_bot'):
                twitch_service.twitch_bot.conversation_mode = "normal"
                logger.debug("Synced conversation_mode to 'normal'")
            
            # Play victory/defeat sound
            # The GameResultService will determine the winner and play the appropriate sound
            # We need to get the game result from the event data
            if self.audio_service and config.PLAYER_INTROS_ENABLED:
                data = event.data or {}
                game_info = data.get('raw_data')
                
                if game_info and hasattr(game_info, 'get_player_names'):
                    try:
                        # Get winners and losers
                        winners = game_info.get_player_names(result_filter='Victory')
                        losers = game_info.get_player_names(result_filter='Defeat')
                        
                        # Check if streamer won or lost
                        streamer_won = config.STREAMER_NICKNAME in winners
                        streamer_lost = config.STREAMER_NICKNAME in losers
                        
                        if streamer_won:
                            logger.info("Playing Victory Sound via AudioService")
                            await self.audio_service.play_sound("victory")
                        elif streamer_lost:
                            logger.info("Playing Defeat Sound via AudioService")
                            await self.audio_service.play_sound("defeat")
                        else:
                            logger.debug("Streamer not in game - no sound played")
                    except Exception as e:
                        logger.error(f"Error determining game result for sound: {e}")
    
    def stop(self):
        self.running = False
