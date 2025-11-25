import logging
import asyncio
import os
import json
import time
from typing import List, Optional, Any, Dict
from core.interfaces import IChatService, IReplayRepository
from models.game_info import GameInfo
from utils.file_utils import find_recent_file_within_time
from utils import tokensArray
from settings import config
import spawningtool.parser
from core.game_summarizer import GameSummarizer

logger = logging.getLogger(__name__)

class GameResultService:
    def __init__(self, replay_repo: IReplayRepository, chat_services: List[IChatService], pattern_learner=None):
        self.replay_repo = replay_repo
        self.chat_services = chat_services
        self.pattern_learner = pattern_learner
        self.last_processed_replay = None
        
    async def process_game_end(self, game_info: GameInfo):
        """
        Orchestrates the end-of-game processing:
        1. Find and parse replay
        2. Update database
        3. Announce results
        4. Trigger pattern learning
        """
        logger.info("Processing game end results...")
        
        # Wait for SC2 to finish writing replay file
        # Polling optimization: check every 1s for up to 15s
        logger.info("Waiting for replay file...")
        replay_path = None
        loop = asyncio.get_running_loop()
        
        for _ in range(15):
            await asyncio.sleep(1)
            try:
                replay_path = await loop.run_in_executor(
                    None, 
                    self._find_replay_file, 
                    config.REPLAYS_FOLDER
                )
                if replay_path and replay_path != self.last_processed_replay:
                    logger.info(f"Replay file detected immediately: {replay_path}")
                    break
            except Exception as e:
                logger.debug(f"Replay search attempt failed: {e}")
        
        # Final check if loop finished without success
        if not replay_path or replay_path == self.last_processed_replay:
             # Try one last time if polling didn't catch it
             pass # Logic flows to existing check below
        
        # 1. Find Replay (Final Confirmation)
        if not replay_path:
            try:
                # Check settings to ignore previous results on startup
                if config.IGNORE_PREVIOUS_GAME_RESULTS_ON_FIRST_RUN and self.last_processed_replay is None:
                    # On first run, strictly check against bot start time logic or very tight window
                    # If we are starting the bot, we only want results from NOW onwards.
                    # Any replay created BEFORE the bot started (or 30 seconds ago) is "old history".
                    time_window = 0.5 # 30 seconds - essentially "just happened"
                else:
                    # Normal operation - check last 2 mins
                    time_window = 2
                    
                replay_path = await loop.run_in_executor(
                    None, 
                    find_recent_file_within_time, # Use the imported function directly
                    config.REPLAYS_FOLDER,
                    config.REPLAYS_FILE_EXTENSION,
                    time_window, # minutes
                    0, # retries
                    logger,
                    self.last_processed_replay
                )
            except Exception as e:
                logger.error(f"Error finding replay file: {e}")
                return
        
        if not replay_path:
            logger.warning("No recent replay file found.")
            return
            
        if replay_path == self.last_processed_replay:
            logger.info("Replay already processed. Skipping.")
            return
            
        self.last_processed_replay = replay_path
        logger.info(f"Found new replay: {replay_path}")

        # 2. Parse Replay
        try:
            replay_data = await loop.run_in_executor(
                None,
                self._parse_replay,
                replay_path
            )
            logger.debug(f"Successfully parsed replay: {replay_path}")
        except Exception as e:
            logger.error(f"Error parsing replay: {e}")
            return
        
        # 3. Save to DB
        try:
            # Generate summary string required by legacy DB schema
            winning_players = ', '.join(game_info.get_player_names(result_filter='Victory'))
            losing_players = ', '.join(game_info.get_player_names(result_filter='Defeat'))
            
            summary = GameSummarizer.generate_summary(replay_data, winning_players, losing_players)
            
            # Use Repository (handles executor/async)
            await self.replay_repo.save_replay(summary)
            logger.info("Saved replay summary to DB")
            
            # TODO: Insert individual player history (legacy does this too)
            
        except Exception as e:
            logger.error(f"Error saving to DB: {e}")
            # Continue execution even if DB fails (we still want to announce)
        
        # 4. Announce Result (using legacy game_ended handler for proper observer logic)
        try:
            from api.game_event_utils.game_ended_handler import game_ended
            
            # Prepare data for legacy handler
            game_player_names = ', '.join(game_info.get_player_names())
            winning_players = ', '.join(game_info.get_player_names(result_filter='Victory'))
            losing_players = ', '.join(game_info.get_player_names(result_filter='Defeat'))
            
            # Get the twitch_bot instance to pass to legacy handler
            twitch_bot = None
            for service in self.chat_services:
                if hasattr(service, 'twitch_bot'):
                    twitch_bot = service.twitch_bot
                    break
            
            if twitch_bot:
                # Set total_seconds on twitch_bot (required by game_ended handler)
                if replay_data:
                    try:
                        frames = replay_data.get('frames', 0)
                        fps = replay_data.get('frames_per_second', 22.4)
                        if fps > 0:
                            twitch_bot.total_seconds = frames / fps
                            logger.debug(f"Set twitch_bot.total_seconds = {twitch_bot.total_seconds}")
                        else:
                            twitch_bot.total_seconds = 0
                    except Exception as e:
                        logger.error(f"Error calculating total_seconds: {e}")
                        twitch_bot.total_seconds = 0
                else:
                    twitch_bot.total_seconds = 0
                
                # Call legacy game_ended which has observer detection logic
                msg = await loop.run_in_executor(
                    None,
                    game_ended,
                    twitch_bot,
                    game_player_names,
                    winning_players,
                    losing_players,
                    logger
                )
                
                # Send the properly formatted message
                for service in self.chat_services:
                    try:
                        await service.send_message("channel", msg)
                    except Exception as e:
                        logger.error(f"Error sending announcement to service: {e}")
            else:
                # Fallback if twitch_bot not available
                winner = game_info.get_winner()
                if winner:
                    msg = f"Game Over! Winner: {winner}"
                    for service in self.chat_services:
                        try:
                            await service.send_message("channel", msg)
                        except Exception as e:
                            logger.error(f"Error sending announcement to service: {e}")
        except Exception as e:
            logger.error(f"Error generating game end announcement: {e}")
        
        # 5. Generate AI Commentary (concise one-sentence summary)
        if not config.OPENAI_DISABLED and replay_data:
            try:
                logger.debug("Generating AI replay analysis commentary...")
                
                # Build CONCISE summary for AI analysis
                # Extract key stats for a SHORT analysis prompt
                winning_players_str = winning_players if winning_players else "Unknown"
                losing_players_str = losing_players if losing_players else "Unknown"
                
                # Get game duration
                frames = replay_data.get('frames', 0)
                fps = replay_data.get('frames_per_second', 22.4)
                duration_seconds = frames / fps if fps > 0 else 0
                duration_str = f"{int(duration_seconds // 60)}m {int(duration_seconds % 60)}s"
                
                # Create a CONCISE prompt asking for ONE sentence
                concise_prompt = f"Provide ONE concise sentence (max 20 words) summarizing this StarCraft 2 game:\n\n"
                concise_prompt += f"Winner: {winning_players_str}\n"
                concise_prompt += f"Loser: {losing_players_str}\n"
                concise_prompt += f"Duration: {duration_str}\n"
                concise_prompt += f"Map: {replay_data.get('map', 'Unknown')}\n\n"
                concise_prompt += "Your ONE sentence summary:"
                
                # Get twitch_bot to send the message
                twitch_bot = None
                for service in self.chat_services:
                    if hasattr(service, 'twitch_bot'):
                        twitch_bot = service.twitch_bot
                        break
                
                if twitch_bot:
                    from api.chat_utils import send_prompt_to_openai
                    
                    # Call OpenAI directly for concise response
                    completion = await loop.run_in_executor(
                        None,
                        send_prompt_to_openai,
                        concise_prompt
                    )
                    
                    if completion and completion.choices and completion.choices[0].message:
                        ai_commentary = completion.choices[0].message.content.strip()
                        
                        # Send the ONE sentence to Twitch
                        for service in self.chat_services:
                            try:
                                await service.send_message("channel", ai_commentary)
                                safe_commentary = tokensArray.replace_non_ascii(ai_commentary[:100], replacement='?')
                                logger.info(f"Sent AI commentary: {safe_commentary}")
                            except Exception as e:
                                logger.error(f"Error sending AI commentary: {e}")
                    else:
                        logger.warning("No valid AI commentary generated")
                else:
                    logger.warning("TwitchBot not available - skipping AI commentary")
            except Exception as e:
                logger.error(f"Error generating AI commentary: {e}")
        
        # 6. Trigger Pattern Learning (Migrated Logic)
        if self.pattern_learner:
            logger.info("Pattern Learning: Triggering (Async)")
            
            # Check requirements: 1v1 game, not abandoned
            total_players = game_info.total_players
            # We need total_seconds from the replay parse, which is in replay_data['unix_timestamp']? 
            # No, it's calculated. We'll use a simple check for now or extract from replay_data if available.
            
            # Replay parser gives us game length
            game_duration_seconds = 0
            if replay_data:
                # Copy logic from api/game_event_utils/game_ended_handler.py
                # def calculate_game_duration(replay_data, logger):
                #     frames = replay_data['frames']
                #     frames_per_second = replay_data['frames_per_second']
                #     total_seconds = frames / frames_per_second
                
                try:
                     frames = replay_data.get('frames', 0)
                     fps = replay_data.get('frames_per_second', 22.4) # Default to Faster speed if missing
                     if fps > 0:
                        game_duration_seconds = frames / fps
                except Exception as e:
                    logger.error(f"Error calculating game duration: {e}")
                    
                logger.debug(f"Game Duration Check: Found {game_duration_seconds}s (Threshold: {config.ABANDONED_GAME_THRESHOLD}s)")
            
            is_1v1 = total_players == 2
            is_long_enough = game_duration_seconds >= config.ABANDONED_GAME_THRESHOLD
            
            # Check if streamer played (not just observing)
            # Logic from legacy: compare players in replay to config.SC2_PLAYER_ACCOUNTS
            streamer_played = False
            if replay_data and 'players' in replay_data:
                player_accounts_lower = [name.lower() for name in config.SC2_PLAYER_ACCOUNTS]
                for p_key, p_data in replay_data['players'].items():
                    if p_data['name'].lower() in player_accounts_lower:
                        streamer_played = True
                        break
            
            if is_1v1 and is_long_enough and streamer_played:
                # Define delayed task to mimic legacy behavior
                async def delayed_learning_trigger():
                    logger.info(f"Pattern Learning: Waiting {config.PATTERN_LEARNING_DELAY_SECONDS}s before analysis...")
                    await asyncio.sleep(config.PATTERN_LEARNING_DELAY_SECONDS)
                    
                    try:
                        # Prepare data for pattern learner
                        # We need to reconstruct game_player_names, winning_players, losing_players
                        # But we already have replay_data which is what we really need
                        
                        # Legacy used `_prepare_game_data_for_comment` which essentially extracted this info
                        # We can manually construct the `game_data` dict expected by `_display_pattern_validation`
                        
                        # Find opponent
                        opponent_name = "Unknown"
                        opponent_race = "Unknown"
                        result = "Unknown"
                        
                        player_accounts_lower = [name.lower() for name in config.SC2_PLAYER_ACCOUNTS]
                        
                        for p_key, p_data in replay_data['players'].items():
                            if p_data['name'].lower() not in player_accounts_lower:
                                opponent_name = p_data['name']
                                opponent_race = p_data['race']
                                # Determine result relative to STREAMER
                                # If opponent won, streamer lost.
                                if p_data['is_winner']: 
                                    result = "Defeat" 
                                else: 
                                    result = "Victory"
                                break
                                
                        game_data = {
                            'opponent_name': opponent_name,
                            'opponent_race': opponent_race,
                            'map': replay_data['map'],
                            'date': replay_data['unix_timestamp'],
                            'result': result,
                            'duration': game_duration_seconds,
                            'build_order': [] # Extracted below
                        }
                        
                        # Extract opponent build order
                        if 'players' in replay_data:
                            for p_key, p_data in replay_data['players'].items():
                                if p_data['name'] == opponent_name:
                                    game_data['build_order'] = p_data.get('buildOrder', [])
                                    break
                        
                        # Trigger Display (Validation)
                        # We need to call the legacy display method or reimplement it
                        # Since pattern_learner is likely the TwitchBot instance (legacy), we can call it?
                        # Or pattern_learner is the SC2PatternLearner instance?
                        # In run_core.py: pattern_learner=getattr(twitch_bot_legacy, 'pattern_learner', None)
                        # So it's the SC2PatternLearner instance.
                        
                        # The legacy code called `self._display_pattern_validation(game_data, logger)` on TwitchBot
                        # which then used `get_ml_analyzer`.
                        
                        # We will try to use the pattern learner directly if possible, or ask BotCore to display
                        logger.info(f"Pattern Learning: analyzing vs {opponent_name} ({opponent_race})")
                        
                        # Use the TwitchBot legacy instance to display if available (for now, to ensure compatibility)
                        # We can access it via chat_services if we must, or just logging for now
                        twitch_service = next((s for s in self.chat_services if s.get_platform_name() == 'twitch'), None)
                        if twitch_service and hasattr(twitch_service, 'twitch_bot'):
                             # This is the Legacy TwitchBot instance
                             # It has the complex logic for display and context setting
                             twitch_bot = twitch_service.twitch_bot
                             if hasattr(twitch_bot, '_display_pattern_validation'):
                                 # We need to inject last_replay_data if it's missing, as _prepare_game_data relies on it
                                 # or passes it via game_data.
                                 # The legacy method uses `game_data` passed to it, but also checks `self.last_replay_data`
                                 # for some fallbacks. Ideally `game_data` has everything.
                                 
                                 # Invoke the legacy method to handle the complex UI/Chat interaction
                                 twitch_bot._display_pattern_validation(game_data, logger)
                                 logger.info("Invoked legacy pattern validation display.")
                             else:
                                 logger.warning("TwitchBot does not have _display_pattern_validation method.")
                                 
                                 # Fallback to simple prompt if method missing
                                 prompt_msg = f"Game vs {opponent_name} ({opponent_race}) analyzed. Result: {result}. Type 'player comment <text>' to save notes."
                                 await twitch_service.send_message("channel", prompt_msg)
                        else:
                             logger.warning("Could not find TwitchBot instance for pattern validation.")

                    except Exception as e:
                        logger.error(f"Pattern Learning Error: {e}")

                # Schedule the task
                asyncio.create_task(delayed_learning_trigger())
            else:
                logger.info(f"Pattern Learning Skipped: 1v1={is_1v1}, Long={is_long_enough}, Streamer={streamer_played}")

    def _find_replay_file(self, folder):
        # Wraps legacy utility
        return find_recent_file_within_time(
            folder,
            config.REPLAYS_FILE_EXTENSION,
            2, # minutes
            0, # retries
            logger,
            self.last_processed_replay
        )
        
    def _parse_replay(self, path):
        return spawningtool.parser.parse_replay(path)
