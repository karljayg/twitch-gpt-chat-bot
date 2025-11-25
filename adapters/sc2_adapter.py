import asyncio
import logging
import time
import os
from typing import Optional, Any
from datetime import datetime
from core.interfaces import IGameStateProvider
from core.bot import BotCore
from core.events import GameStateEvent
from api.sc2_game_utils import check_SC2_game_status
# from api.sc2_game_utils import handle_SC2_game_results # Completely disabled
import settings.config as config

logger = logging.getLogger(__name__)

# SC2 Client Activity Log
SC2_ACTIVITY_LOG = "sc2client_activity_log.txt"
MAX_LOG_SIZE = 100 * 1024  # 100KB

class SC2Adapter(IGameStateProvider):
    def __init__(self, bot_core: BotCore, game_result_service=None):
        self.bot_core = bot_core
        self.game_result_service = game_result_service
        self.current_game = None
        self.previous_game = None
        self.running = False
        self.heartbeat_counter = 0
        self.heartbeat_interval = config.HEARTBEAT_MYSQL  # Number of iterations before DB heartbeat
        
    def get_current_game_state(self) -> Any:
        return self.current_game

    def get_last_game_result(self) -> Any:
        # Ideally this would return the result of the previous game
        return self.previous_game
        
    def _get_legacy_twitch_bot(self):
        """Helper to retrieve the legacy TwitchBot instance from the BotCore adapters"""
        twitch_service = self.bot_core.chat_services.get('twitch')
        if twitch_service and hasattr(twitch_service, 'twitch_bot'):
            return twitch_service.twitch_bot
        return None

    async def start_monitoring(self):
        """
        Async loop to monitor SC2 game status. 
        Replaces the threaded monitor_game in twitch_bot.py.
        """
        self.running = True
        logger.info("SC2 Monitoring started")
        
        # Initial Poll to set baseline state without triggering events
        # This prevents "Game Over" spam on bot restart if the game is already in 'MATCH_ENDED' state
        try:
            loop = asyncio.get_event_loop()
            initial_game = await loop.run_in_executor(None, check_SC2_game_status, logger)
            self.current_game = initial_game
            self.previous_game = initial_game
            status = initial_game.get_status() if initial_game else 'None'
            logger.info(f"SC2 Monitoring initialized. Current state: {status}")
        except Exception as e:
            logger.error(f"Failed to initialize SC2 state: {e}")
        
        while self.running:
            monitoring_success = True # Assume success
            try:
                # We wrap the synchronous check_SC2_game_status in executor
                # to avoid blocking the async loop
                loop = asyncio.get_event_loop()
                
                # Poll SC2 API
                current_game = await loop.run_in_executor(None, check_SC2_game_status, logger)
                
                # Log SC2 client status to file
                self._log_sc2_status(current_game, monitoring_success)
                
                # Detect State Change
                if self._has_state_changed(self.current_game, current_game):
                    old_status = self.current_game.get_status() if self.current_game and hasattr(self.current_game, 'get_status') else "None"
                    new_status = current_game.get_status() if current_game and hasattr(current_game, 'get_status') else "None"
                    logger.info(f"SC2 State Change Detected: {old_status} -> {new_status}")
                    
                    # 1. Notify Core (for simple status updates)
                    event = self._create_game_event(current_game)
                    self.bot_core.add_event(event)
                    logger.debug(f"Pushed {event.event_type} event to BotCore")
                    
                    # 2. Trigger GameResultService (New Architecture)
                    # Handle both MATCH_ENDED and REPLAY_ENDED (user watched replay immediately after game)
                    status = current_game.get_status() if current_game else "None"
                    if status in ("MATCH_ENDED", "REPLAY_ENDED") and self.game_result_service:
                        logger.info(f"Triggering GameResultService.process_game_end for {status} (Async Task)")
                        # Run as task to not block monitoring loop
                        asyncio.create_task(self.game_result_service.process_game_end(current_game))
                    
                    # Note: Legacy logic (handle_SC2_game_results) is intentionally disabled
                    # to prevent double processing of game results. All logic is now in GameResultService.

                self.previous_game = self.current_game
                self.current_game = current_game
                
            except Exception as e:
                monitoring_success = False
                # Handle specific known error that indicates connection failure/GameInfo crash
                if "isReplay" in str(e):
                    print("o", end="", flush=True)
                else:
                    logger.error(f"Error in SC2 monitoring: {e}")
                    print("o", end="", flush=True)
            
            # Increment heartbeat counter
            self.heartbeat_counter += 1
            
            # Check if it's time to send a database heartbeat
            if self.heartbeat_counter >= self.heartbeat_interval:
                try:
                    twitch_bot = self._get_legacy_twitch_bot()
                    if twitch_bot and hasattr(twitch_bot, 'db'):
                        twitch_bot.db.keep_connection_alive()
                        self.heartbeat_counter = 0  # Reset after successful heartbeat
                        print("+", end="", flush=True)  # DB heartbeat indicator
                    else:
                        # No DB available, just reset counter
                        self.heartbeat_counter = 0
                        if monitoring_success:
                            print(".", end="", flush=True)
                except Exception as e:
                    logger.error(f"Error during database heartbeat: {e}")
                    self.heartbeat_counter = 0
                    print("o", end="", flush=True)
            else:
                # Normal heartbeat indicator
                if monitoring_success:
                    print(".", end="", flush=True)
            
            # Sleep interval from config
            await asyncio.sleep(config.MONITOR_GAME_SLEEP_SECONDS)

    def stop(self):
        self.running = False

    def _log_sc2_status(self, game_data, success):
        """Log SC2 client status to activity log file"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status = game_data.get_status() if game_data and hasattr(game_data, 'get_status') else "None"
            
            # Get player info if available
            players = "No players"
            if game_data and hasattr(game_data, 'get_player_names'):
                try:
                    player_list = game_data.get_player_names()
                    players = ", ".join(player_list) if player_list else "No players"
                except:
                    players = "Error getting players"
            
            # Get display time if available
            display_time = getattr(game_data, 'displayTime', 'N/A')
            
            # Get isReplay flag
            is_replay = getattr(game_data, 'isReplay', 'N/A')
            
            log_entry = f"{timestamp} | Status: {status} | Players: {players} | Time: {display_time}s | isReplay: {is_replay} | Success: {success}\n"
            
            # Check file size and roll over if needed
            if os.path.exists(SC2_ACTIVITY_LOG):
                file_size = os.path.getsize(SC2_ACTIVITY_LOG)
                if file_size > MAX_LOG_SIZE:
                    # Keep only the last 50KB of the log
                    with open(SC2_ACTIVITY_LOG, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    # Calculate approximate number of lines to keep
                    # Assuming average line length, keep about half the file
                    lines_to_keep = len(lines) // 2
                    
                    with open(SC2_ACTIVITY_LOG, 'w', encoding='utf-8') as f:
                        f.write(f"--- Log rolled over at {timestamp} (exceeded {MAX_LOG_SIZE} bytes) ---\n")
                        f.writelines(lines[-lines_to_keep:])
            
            with open(SC2_ACTIVITY_LOG, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            logger.debug(f"Error writing to SC2 activity log: {e}")

    def _has_state_changed(self, old_game, new_game):
        """
        Determine if significant state change occurred.
        Checks:
        1. Status changed
        2. MATCH_STARTED with no players -> MATCH_STARTED with players (new game started)
        """
        old_status = old_game.get_status() if old_game and hasattr(old_game, 'get_status') else "None"
        new_status = new_game.get_status() if new_game and hasattr(new_game, 'get_status') else "None"
        
        # Basic status change
        if old_status != new_status:
            return True
        
        # Special case: MATCH_STARTED -> MATCH_STARTED but players changed
        # This detects when matchmaking screen (no players) transitions to actual game (with players)
        if old_status == "MATCH_STARTED" and new_status == "MATCH_STARTED":
            try:
                old_players = old_game.get_player_names() if old_game and hasattr(old_game, 'get_player_names') else []
                new_players = new_game.get_player_names() if new_game and hasattr(new_game, 'get_player_names') else []
                
                # If we transition from no players to having players, it's a new game
                if (not old_players or len(old_players) == 0) and (new_players and len(new_players) > 0):
                    logger.info(f"SC2 New Game Detected: Players loaded ({', '.join(new_players)})")
                    return True
            except Exception as e:
                logger.debug(f"Error checking player change: {e}")
        
        return False

    def _create_game_event(self, game_data) -> GameStateEvent:
        """
        Convert SC2 game object into a Core Event.
        """
        status = game_data.get_status() if game_data and hasattr(game_data, 'get_status') else "unknown"
        
        # Map SC2 status to Event Type
        event_type = "status_change"
        if status == "MATCH_STARTED":
            event_type = "game_started"
        elif status in ("MATCH_ENDED", "REPLAY_ENDED"):
            # Both MATCH_ENDED and REPLAY_ENDED indicate game completion
            # REPLAY_ENDED happens when user immediately watches replay after game
            event_type = "game_ended"
            
        return GameStateEvent(
            event_type=event_type,
            data={
                "status": status,
                "raw_data": game_data
            }
        )
