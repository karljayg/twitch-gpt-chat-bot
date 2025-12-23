import logging
import asyncio
import os
import json
import time
from typing import List, Optional, Any, Dict
from core.interfaces import IChatService, IReplayRepository
from models.game_info import GameInfo
from utils.file_utils import find_recent_file_within_time, find_latest_file
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
        
    async def process_game_end(self, game_info: GameInfo, replay_data: Optional[dict] = None, skip_duplicate_check: bool = False):
        logger.debug(f"process_game_end called: replay_data={'provided' if replay_data else 'None'}, skip_duplicate_check={skip_duplicate_check}")
        """
        Orchestrates the end-of-game processing:
        1. Find and parse replay (or use provided replay_data)
        2. Update database
        3. Announce results
        4. Trigger pattern learning
        
        Args:
            game_info: GameInfo object from SC2 API
            replay_data: Optional pre-parsed replay data (for retry scenarios)
            skip_duplicate_check: If True, process even if replay was already processed
        """
        logger.info("Processing game end results...")
        
        # Get event loop early - needed for both normal and retry paths
        loop = asyncio.get_running_loop()
        
        # Check if game is too short (for skipping analysis/ML, but still save to DB)
        game_duration_seconds = game_info.displayTime
        is_too_short = game_duration_seconds < 60
        
        # If replay_data is provided, skip file finding/parsing
        if not replay_data:
            # Normal flow: find and parse replay file
            # Wait for SC2 to finish writing replay file
            # Initial wait to give SC2 time to finish writing
            logger.info("Waiting for replay file...")
            await asyncio.sleep(3)
            
            # Polling optimization: check every 1s for up to 15s
            replay_path = None
            
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
                
            if replay_path == self.last_processed_replay and not skip_duplicate_check:
                logger.info("Replay already processed. Skipping.")
                return
                
            if not skip_duplicate_check:
                self.last_processed_replay = replay_path
            logger.info(f"Found new replay: {replay_path}")

            # 2. Parse Replay
            # Wait a bit for file to finish writing
            await asyncio.sleep(3)
            
            # Validate file before parsing to avoid segfaults
            if not os.path.exists(replay_path):
                logger.error(f"Replay file does not exist: {replay_path}")
                return
            
            # Check if file is locked (still being written by SC2)
            # Retry with increasing delays to handle file sync delays
            max_retries = 3
            retry_delay = 3  # Start with 3 seconds
            file_locked = True
            
            for attempt in range(max_retries):
                try:
                    # Check file size first (if file is locked, this might also fail)
                    file_size = os.path.getsize(replay_path)
                    if file_size == 0:
                        logger.warning(f"Replay file is empty, waiting... ({attempt + 1}/{max_retries})")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            logger.error(f"Replay file still empty after {max_retries} attempts: {replay_path}")
                            return
                    
                    if file_size < 1000:  # SC2 replays are typically > 1KB
                        logger.warning(f"Replay file suspiciously small ({file_size} bytes): {replay_path}")
                    
                    # Try to open file in append mode - if locked, this will fail
                    with open(replay_path, 'a+b') as f:
                        pass
                    
                    # File is accessible - check if size is stable (not still writing)
                    await asyncio.sleep(1)
                    new_size = os.path.getsize(replay_path)
                    if new_size != file_size:
                        logger.debug(f"File size changed ({file_size} -> {new_size}), still writing... ({attempt + 1}/{max_retries})")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay)
                            continue
                    
                    # File is unlocked and size is stable
                    file_locked = False
                    logger.info(f"Replay file is ready: {replay_path} ({new_size} bytes)")
                    break
                    
                except (IOError, OSError, PermissionError) as e:
                    if attempt < max_retries - 1:
                        logger.debug(f"Replay file locked, retrying in {retry_delay}s... ({attempt + 1}/{max_retries}): {replay_path}")
                        await asyncio.sleep(retry_delay)
                        retry_delay += 1  # Increase delay for each retry (3s, 4s, 5s, 6s, 7s)
                    else:
                        logger.error(f"Replay file still locked after {max_retries} attempts, skipping: {replay_path} - {e}")
                        return
            
            if file_locked:
                logger.error(f"Cannot parse locked replay file: {replay_path}")
                return
            
            try:
                logger.debug(f"Attempting to parse replay: {replay_path} ({file_size} bytes)")
                replay_data = await loop.run_in_executor(
                    None,
                    self._parse_replay,
                    replay_path
                )
                logger.debug(f"Successfully parsed replay: {replay_path}")
                
                # Save JSON file for potential retry (even if processing fails later)
                try:
                    from api.game_event_utils.game_ended_handler import save_file
                    save_file(replay_data, 'json', logger)
                except Exception as e:
                    logger.warning(f"Failed to save JSON file for retry: {e}")
            except Exception as e:
                logger.error(f"Error parsing replay: {e}", exc_info=True)
                # Don't crash the bot - just skip this replay
                return
            except BaseException as e:
                # Catch even SystemExit/KeyboardInterrupt to prevent crashes
                logger.critical(f"Critical error parsing replay (may be segfault): {e}", exc_info=True)
                return
        else:
            logger.info("Using provided replay data (retry mode)")
        
        # Continue with processing (both normal and retry paths converge here)
        
        # 3. Save to DB
        try:
            # Generate summary string required by legacy DB schema
            winning_players = ', '.join(game_info.get_player_names(result_filter='Victory'))
            losing_players = ', '.join(game_info.get_player_names(result_filter='Defeat'))
            
            summary = GameSummarizer.generate_summary(replay_data, winning_players, losing_players)
            
            # Save summary to file for retry capability (created after parsing, used if processing fails)
            try:
                from api.game_event_utils.game_ended_handler import save_file
                save_file(summary, 'summary', logger)
            except Exception as e:
                logger.warning(f"Failed to save replay summary file for retry: {e}")
            
            # Use Repository (handles executor/async)
            await self.replay_repo.save_replay(summary)
            logger.info("Saved replay summary to DB")
            
            # TODO: Insert individual player history (legacy does this too)
            
        except Exception as e:
            logger.error(f"Error saving to DB: {e}")
            # Continue execution even if DB fails (we still want to announce)
        
        # Check if game is too short - skip analysis/ML but still announce
        if is_too_short:
            logger.info(f"Game too short ({game_duration_seconds}s) - skipping analysis and ML, but DB saved")
            
            # Extract opponent info for skip message
            opponent_name = "Unknown"
            opponent_race = "Unknown"
            map_name = replay_data.get('map', 'Unknown') if replay_data else "Unknown"
            
            try:
                # Find opponent (not streamer)
                for player in game_info.players:
                    if not game_info._is_streamer_account(player.get('name', '')):
                        opponent_name = player.get('name', 'Unknown')
                        opponent_race = game_info.get_opponent_race(opponent_name)
                        break
            except Exception as e:
                logger.debug(f"Error extracting opponent info for short game: {e}")
            
            # Generate varied skip message via OpenAI
            try:
                from api.chat_utils import send_prompt_to_openai
                map_part = f" on {map_name}" if map_name != "Unknown" else ""
                prompt = f"""Generate a short, casual message saying a game was skipped because it was too short (less than 1 minute). 
Include: opponent race ({opponent_race}), opponent name ({opponent_name}){map_part}.
Keep it brief and varied - don't use the exact same wording every time.
Examples: "Game skipped, too short vs {opponent_race} {opponent_name}{map_part}" or "Skipped {opponent_name}'s {opponent_race} game{map_part} - ended too quickly"
Generate ONE short message only, no explanation."""
                
                completion = send_prompt_to_openai(prompt)
                if completion and completion.choices and completion.choices[0].message:
                    skip_message = completion.choices[0].message.content.strip()
                else:
                    map_part = f" on {map_name}" if map_name != "Unknown" else ""
                    skip_message = f"Game skipped, too short vs {opponent_race} {opponent_name}{map_part}"
            except Exception as e:
                logger.error(f"Error generating skip message: {e}")
                map_part = f" on {map_name}" if map_name != "Unknown" else ""
                skip_message = f"Game skipped, too short vs {opponent_race} {opponent_name}{map_part}"
            
            # Send skip message to all chat services
            for service in self.chat_services:
                try:
                    await service.send_message("chat", skip_message)
                except Exception as e:
                    logger.error(f"Error sending skip message to {service.get_platform_name()}: {e}")
            
            # Skip AI commentary and pattern learning, but still announce result
            # (Announcement happens below, so we'll let it continue)
        
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
        
        # 5. Generate AI Commentary (concise one-sentence summary) - Skip if game too short or not 1v1
        is_1v1_game = game_info.total_players == 2
        if not is_too_short and not config.OPENAI_DISABLED and replay_data and is_1v1_game:
            try:
                logger.debug("Generating AI replay analysis commentary...")
                
                # Build CONCISE summary for AI analysis
                # Extract key stats for a SHORT analysis prompt
                winning_players_str = winning_players if winning_players else "Unknown"
                losing_players_str = losing_players if losing_players else "Unknown"
                
                # Get game duration from replay_summary (same calculation used in GameSummarizer)
                duration_info = GameSummarizer.calculate_duration(replay_data)
                duration_seconds = duration_info['totalSeconds']
                duration_str = duration_info['gameDuration']
                
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
        
        # 6a. Strategy Summary for ALL game types (1v1, 2v2, 3v3, etc.)
        # Loops through each player and checks for pattern matches
        if not is_too_short and replay_data and 'players' in replay_data:
            try:
                from api.ml_opponent_analyzer import get_ml_analyzer
                from core.strategy_summary_service import get_game_summary
                
                analyzer = get_ml_analyzer()
                strategy_summary = get_game_summary(replay_data, analyzer, min_similarity=0.70)
                
                if strategy_summary:
                    logger.info(f"Strategy Summary: {strategy_summary}")
                    # Send to Twitch
                    for service in self.chat_services:
                        try:
                            await service.send_message("channel", strategy_summary)
                        except Exception as e:
                            logger.debug(f"Error sending strategy summary: {e}")
                else:
                    logger.debug("No high-confidence strategy matches for any player")
            except Exception as e:
                logger.debug(f"Strategy summary error: {e}")
        
        # 6b. Trigger Pattern Learning (Migrated Logic) - Skip if game too short
        if not is_too_short and self.pattern_learner:
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
                                    build_order = p_data.get('buildOrder', [])
                                    logger.info(f"Extracted {len(build_order)} build order steps for {opponent_name} from replay_data")
                                    game_data['build_order'] = build_order
                                    break
                        
                        # === PATTERN MATCHING COMPARISON ===
                        # Run both pattern matching methods and display top 3 from each
                        try:
                            from api.ml_opponent_analyzer import get_ml_analyzer
                            analyzer = get_ml_analyzer()
                            
                            build_order = game_data.get('build_order', [])
                            if build_order:
                                logger.info("=" * 50)
                                logger.info("PATTERN MATCHING COMPARISON")
                                
                                # 1. Pattern Learning (comments.json)
                                comments_matches = analyzer.match_build_against_all_patterns(
                                    build_order, opponent_race, logger
                                )
                                if comments_matches:
                                    best = comments_matches[0]
                                    logger.info(f"Best match: '{best.get('comment', 'Unknown')}' at {best.get('similarity', 0):.2f} similarity")
                                logger.info(f"Pattern Learning (comments.json - {len(build_order)} steps):")
                                if comments_matches:
                                    for i, match in enumerate(comments_matches[:5]):
                                        similarity = match.get('similarity', 0) * 100
                                        comment = match.get('comment', 'Unknown')
                                        logger.info(f"  {i+1}. {similarity:.0f}% - '{comment}'")
                                else:
                                    logger.info("  No matches found")
                                
                                # 2. ML Analysis (patterns.json)
                                patterns_data = analyzer.load_patterns_data()
                                patterns_matches = analyzer._match_build_against_patterns(
                                    build_order, patterns_data, opponent_race, logger
                                )
                                if patterns_matches:
                                    best = patterns_matches[0]
                                    logger.info(f"Best match: '{best.get('comment', 'Unknown')}' at {best.get('similarity', 0):.2f} similarity")
                                logger.info(f"ML Analysis (patterns.json - DB text extraction):")
                                if patterns_matches:
                                    for i, match in enumerate(patterns_matches[:5]):
                                        similarity = match.get('similarity', 0) * 100
                                        comment = match.get('comment', 'Unknown')
                                        logger.info(f"  {i+1}. {similarity:.0f}% - '{comment}'")
                                else:
                                    logger.info("  No matches found")
                                
                                logger.info("=" * 50)
                                    
                        except Exception as e:
                            logger.error(f"Pattern matching comparison error: {e}")
                        
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

    async def retry_last_game(self):
        """Retry processing - finds most recent replay and processes it normally"""
        logger.info("Retrying last game processing...")
        
        # Find most recent replay file (for retry, just get the latest file regardless of age)
        loop = asyncio.get_running_loop()
        try:
            replay_path = await loop.run_in_executor(
                None,
                find_latest_file,
                config.REPLAYS_FOLDER,
                config.REPLAYS_FILE_EXTENSION,
                logger
            )
        except Exception as e:
            logger.error(f"Error finding replay file for retry: {e}")
            return False
        
        if not replay_path:
            logger.warning("No replay file found for retry.")
            return False
        
        # Verify replay file is recent (within last 24 hours) to avoid processing very old games
        try:
            file_mtime = os.path.getmtime(replay_path)
            import time
            age_seconds = time.time() - file_mtime
            if age_seconds > 86400:  # 24 hours
                logger.warning(f"Replay file is very old ({age_seconds/86400:.1f} days) - may be from previous session. Retry only works for recent failures.")
                return False
        except Exception as e:
            logger.warning(f"Could not check replay file timestamp: {e}")
        
        # Parse replay to get GameInfo and replay_data
        try:
            logger.info(f"Parsing replay for retry: {replay_path}")
            replay_data = await loop.run_in_executor(None, self._parse_replay, replay_path)
            
            if not replay_data:
                logger.error("Failed to parse replay - replay_data is None")
                return False
            
            logger.info(f"Successfully parsed replay, got {len(replay_data.get('players', {}))} players")
            
            # Save JSON file so player comments can access it
            try:
                from api.game_event_utils.game_ended_handler import save_file
                save_file(replay_data, 'json', logger)
                logger.info("Updated last_replay_data.json for retry")
            except Exception as e:
                logger.warning(f"Failed to save JSON file during retry: {e}")
            
            # Reconstruct GameInfo from replay_data
            players = []
            for p_data in replay_data.get('players', {}).values():
                result = 'Victory' if p_data.get('is_winner', False) else 'Defeat'
                players.append({
                    'name': p_data.get('name', 'Unknown'),
                    'race': p_data.get('race', 'Unknown').lower(),
                    'result': result
                })
            
            frames = replay_data.get('frames', 0)
            fps = replay_data.get('frames_per_second', 22.4)
            display_time = frames / fps if fps > 0 else 0
            
            game_info = GameInfo({
                'isReplay': False,
                'players': players,
                'displayTime': display_time
            })
            
            logger.info(f"Reconstructed GameInfo: {len(players)} players, duration={display_time}s")
        except Exception as e:
            logger.error(f"Error parsing replay for retry: {e}", exc_info=True)
            return False
        
        # Call process_game_end with replay_data - it will skip file finding/parsing and process normally
        # skip_duplicate_check allows it to process the same replay again
        try:
            logger.info(f"Calling process_game_end with replay_data (skip_duplicate_check=True), replay_data type: {type(replay_data)}, has players: {bool(replay_data and 'players' in replay_data)}")
            await self.process_game_end(game_info, replay_data=replay_data, skip_duplicate_check=True)
            logger.info("Retry processing completed successfully")
            return True
        except Exception as e:
            logger.error(f"Error during retry processing: {e}", exc_info=True)
            return False

    async def test_replay_by_id(self, replay_id: int) -> str:
        """
        Test strategy summary against a historical replay by ID.
        Looks up replay in DB, finds matching pattern in comments.json, runs strategy summary.
        
        Returns:
            Result message string
        """
        logger.info(f"Testing strategy summary for replay ID: {replay_id}")
        
        # 1. Get replay info from DB
        replay_info = self.replay_repo.db.get_replay_by_id(replay_id)
        if not replay_info:
            return f"Replay ID {replay_id} not found in database"
        
        opponent = replay_info['opponent']
        opponent_race = replay_info['opponent_race']
        map_name = replay_info['map']
        date_str = replay_info['date']
        
        logger.info(f"Found replay: vs {opponent} ({opponent_race}) on {map_name}, {date_str}")
        
        # 2. Load comments.json and find matching entry
        try:
            import json
            
            comments_path = 'data/comments.json'
            with open(comments_path, 'r', encoding='utf-8') as f:
                comments_file = json.load(f)
            
            # Structure is {"comments": [...]}
            comments_data = comments_file.get('comments', [])
            
            # Find matching comment by opponent + date + map
            matching_comment = None
            for comment_entry in comments_data:
                game_data = comment_entry.get('game_data', {})
                entry_opponent = game_data.get('opponent_name', '')
                entry_date = game_data.get('date', '')
                entry_map = game_data.get('map', '')
                
                # Match by opponent name (case-insensitive) and date contains match
                if (entry_opponent.lower() == opponent.lower() and 
                    str(entry_date) in date_str):
                    matching_comment = comment_entry
                    logger.info(f"Found matching comment: '{comment_entry.get('comment', '')}'")
                    break
            
            # 3. Extract build order - try comments.json first, then fall back to DB
            build_order = []
            if matching_comment:
                game_data = matching_comment.get('game_data', {})
                build_order = game_data.get('build_order', [])
                logger.info(f"Found build order from comments.json: {len(build_order)} steps")
            else:
                logger.info(f"No matching comment found for {opponent} on {date_str}")
            
            # If no build order from comments.json, parse from DB's Replay_Summary
            if not build_order:
                replay_summary = replay_info.get('replay_summary', '')
                if replay_summary:
                    build_order = self._parse_build_order_from_summary(replay_summary, opponent)
                    logger.info(f"Parsed {len(build_order)} build steps from DB replay_summary")
                else:
                    logger.warning(f"No replay_summary in DB for replay {replay_id}")
            
            if not build_order:
                return f"Replay {replay_id}: No build order data found"
            
            logger.info(f"Extracted {len(build_order)} build order steps for {opponent} from replay_data")
            
            # 4. Run pattern matching comparison (same as please retry)
            from api.ml_opponent_analyzer import get_ml_analyzer
            analyzer = get_ml_analyzer()
            
            logger.info("=" * 50)
            logger.info("PATTERN MATCHING COMPARISON")
            
            # 1. Pattern Learning (comments.json)
            comments_matches = analyzer.match_build_against_all_patterns(
                build_order, opponent_race, logger
            )
            if comments_matches:
                best = comments_matches[0]
                logger.info(f"Best match: '{best.get('comment', 'Unknown')}' at {best.get('similarity', 0):.2f} similarity")
            logger.info(f"Pattern Learning (comments.json - {len(build_order)} steps):")
            if comments_matches:
                for i, match in enumerate(comments_matches[:5]):
                    similarity = match.get('similarity', 0) * 100
                    comment = match.get('comment', 'Unknown')
                    logger.info(f"  {i+1}. {similarity:.0f}% - '{comment}'")
            else:
                logger.info("  No matches found")
            
            # 2. ML Analysis (patterns.json)
            patterns_data = analyzer.load_patterns_data()
            patterns_matches = analyzer._match_build_against_patterns(
                build_order, patterns_data, opponent_race, logger
            )
            if patterns_matches:
                best = patterns_matches[0]
                logger.info(f"Best match: '{best.get('comment', 'Unknown')}' at {best.get('similarity', 0):.2f} similarity")
            logger.info(f"ML Analysis (patterns.json - DB text extraction):")
            if patterns_matches:
                for i, match in enumerate(patterns_matches[:5]):
                    similarity = match.get('similarity', 0) * 100
                    comment = match.get('comment', 'Unknown')
                    logger.info(f"  {i+1}. {similarity:.0f}% - '{comment}'")
            else:
                logger.info("  No matches found")
            
            logger.info("=" * 50)
            
            # Return summary message
            if comments_matches:
                best = comments_matches[0]
                result_msg = f"Replay {replay_id} vs {opponent}: Best match '{best.get('comment', 'Unknown')}' at {best.get('similarity', 0)*100:.0f}%"
            else:
                result_msg = f"Replay {replay_id} vs {opponent}: No strategy match found"
            
            logger.info(result_msg)
            return result_msg
            
        except FileNotFoundError:
            return "comments.json not found"
        except Exception as e:
            logger.error(f"Error testing replay {replay_id}: {e}", exc_info=True)
            return f"Error: {e}"

    def _parse_build_order_from_summary(self, summary_text: str, player_name: str) -> list:
        """
        Parse a player's build order from the Replay_Summary text.
        
        Format in summary:
            PlayerName's Build Order (first set of steps):
            Time: 0:00, Name: Drone, Supply: 12
            Time: 0:10, Name: Overlord, Supply: 13
            ...
        """
        import re
        build_order = []
        
        # Find the section for this player
        # Match until double newline OR until another player's build order section
        pattern = rf"{re.escape(player_name)}'s Build Order.*?:\n(.*?)(?:\n\n[A-Z]|\n\n|\Z)"
        match = re.search(pattern, summary_text, re.DOTALL | re.IGNORECASE)
        
        if not match:
            return []
        
        build_section = match.group(1)
        
        # Parse each line: "Time: 0:00, Name: Drone, Supply: 12"
        for line in build_section.strip().split('\n'):
            line = line.strip()
            if not line or not line.startswith('Time:'):
                continue
            
            try:
                # Extract time, name, supply
                time_match = re.search(r'Time:\s*(\d+:\d+)', line)
                name_match = re.search(r'Name:\s*(\w+)', line)
                supply_match = re.search(r'Supply:\s*(\d+)', line)
                
                if time_match and name_match:
                    time_str = time_match.group(1)
                    mins, secs = time_str.split(':')
                    time_seconds = int(mins) * 60 + int(secs)
                    
                    build_order.append({
                        'time': time_seconds,
                        'name': name_match.group(1),
                        'supply': int(supply_match.group(1)) if supply_match else 0
                    })
            except Exception:
                continue
        
        return build_order
    
    def _parse_replay_summary(self, summary_text: str):
        """Parse replay_summary.txt format to extract GameInfo and replay_data"""
        lines = summary_text.strip().split('\n')
        
        # Parse header info
        players_str = ""
        map_name = "Unknown"
        region = "Unknown"
        game_type = "Unknown"
        timestamp = 0
        winners_str = ""
        losers_str = ""
        duration_str = ""
        
        # Find where build orders start
        build_order_start_idx = None
        for i, line in enumerate(lines):
            if line.startswith("Players:"):
                players_str = line.split(":", 1)[1].strip()
            elif line.startswith("Map:"):
                map_name = line.split(":", 1)[1].strip()
            elif line.startswith("Region:"):
                region = line.split(":", 1)[1].strip()
            elif line.startswith("Game Type:"):
                game_type = line.split(":", 1)[1].strip()
            elif line.startswith("Timestamp:"):
                timestamp = int(line.split(":", 1)[1].strip())
            elif line.startswith("Winners:"):
                winners_str = line.split(":", 1)[1].strip()
            elif line.startswith("Losers:"):
                losers_str = line.split(":", 1)[1].strip()
            elif line.startswith("Game Duration:"):
                duration_str = line.split(":", 1)[1].strip()
            elif "Build Order" in line and build_order_start_idx is None:
                build_order_start_idx = i
                break  # Found start of build orders
        
        # Parse duration (e.g., "12m 57s")
        display_time = 0
        if duration_str:
            import re
            match = re.match(r'(\d+)m\s*(\d+)s', duration_str)
            if match:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                display_time = minutes * 60 + seconds
        
        # Parse players
        players = []
        player_dict = {}
        
        # Parse "Player1: Race1, Player2: Race2" format
        for player_part in players_str.split(','):
            player_part = player_part.strip()
            if ':' in player_part:
                name, race = player_part.split(':', 1)
                name = name.strip()
                race = race.strip()
                player_dict[name] = race
        
        # Determine results
        winners = [w.strip() for w in winners_str.split(',')] if winners_str else []
        losers = [l.strip() for l in losers_str.split(',')] if losers_str else []
        
        # Build players list with results
        for name, race in player_dict.items():
            if name in winners:
                result = 'Victory'
            elif name in losers:
                result = 'Defeat'
            else:
                result = 'Undecided'
            
            players.append({
                'name': name,
                'race': race.lower(),  # GameInfo expects lowercase
                'result': result
            })
        
        # Create GameInfo
        game_info = GameInfo({
            'isReplay': False,
            'players': players,
            'displayTime': display_time
        })
        
        # Parse build orders from summary file
        opponent_build_order = []
        if build_order_start_idx is not None:
            # Find opponent's build order section
            current_player = None
            for i in range(build_order_start_idx, len(lines)):
                line = lines[i].strip()
                if not line:
                    continue
                
                # Check if this is a new player's build order section
                if "'s Build Order" in line:
                    # Extract player name
                    current_player = line.split("'s Build Order")[0].strip()
                    continue
                
                # Parse build order lines: "Time: 0:00, Name: Drone, Supply: 12"
                if line.startswith("Time:") and current_player:
                    try:
                        # Parse: "Time: 0:00, Name: Drone, Supply: 12"
                        parts = line.split(", ")
                        time_part = parts[0].split(":")[1].strip()  # "0:00"
                        name_part = parts[1].split(":")[1].strip()  # "Drone"
                        
                        # Convert time to seconds
                        if ':' in time_part:
                            minutes, seconds = map(int, time_part.split(':'))
                            time_seconds = minutes * 60 + seconds
                        else:
                            time_seconds = int(time_part)
                        
                        # Find opponent (not streamer)
                        is_opponent = False
                        for p in players:
                            if p['name'] == current_player and not game_info._is_streamer_account(current_player):
                                is_opponent = True
                                break
                        
                        if is_opponent:
                            opponent_build_order.append({
                                'name': name_part,
                                'time': time_seconds
                            })
                    except Exception as e:
                        logger.debug(f"Error parsing build order line: {line} - {e}")
        
        # Create replay_data dict with build orders
        players_dict = {}
        for i, p in enumerate(players):
            player_key = f'player_{i}'
            players_dict[player_key] = {
                'name': p['name'],
                'race': p['race'],
                'is_winner': p['result'] == 'Victory'
            }
            # Add build order for opponent
            if not game_info._is_streamer_account(p['name']) and opponent_build_order:
                players_dict[player_key]['buildOrder'] = opponent_build_order
        
        replay_data = {
            'map': map_name,
            'region': region,
            'game_type': game_type,
            'unix_timestamp': timestamp,
            'players': players_dict,
            'frames': int(display_time * 22.4),  # Approximate
            'frames_per_second': 22.4
        }
        
        return game_info, replay_data
    
    async def _process_with_replay_data_UNUSED(self, game_info: GameInfo, replay_data: dict):
        """Process game end with already-parsed replay data (skips replay file parsing)"""
        game_duration_seconds = game_info.displayTime
        is_too_short = game_duration_seconds < 60
        
        # Save to DB
        try:
            winning_players = ', '.join(game_info.get_player_names(result_filter='Victory'))
            losing_players = ', '.join(game_info.get_player_names(result_filter='Defeat'))
            summary = GameSummarizer.generate_summary(replay_data, winning_players, losing_players)
            await self.replay_repo.save_replay(summary)
            logger.info("Saved replay summary to DB")
        except Exception as e:
            logger.error(f"Error saving to DB: {e}")
        
        # Continue with rest of processing (announcements, pattern learning)
        # This mirrors the logic from process_game_end after replay parsing
        loop = asyncio.get_running_loop()
        
        # Check if game is too short
        if is_too_short:
            logger.info(f"Game too short ({game_duration_seconds}s) - skipping analysis and ML, but DB saved")
            # Extract opponent info for skip message
            opponent_name = "Unknown"
            opponent_race = "Unknown"
            map_name = replay_data.get('map', 'Unknown')
            
            try:
                for player in game_info.players:
                    if not game_info._is_streamer_account(player.get('name', '')):
                        opponent_name = player.get('name', 'Unknown')
                        opponent_race = game_info.get_opponent_race(opponent_name)
                        break
            except Exception as e:
                logger.debug(f"Error extracting opponent info: {e}")
            
            # Generate skip message
            try:
                from api.chat_utils import send_prompt_to_openai
                map_part = f" on {map_name}" if map_name != "Unknown" else ""
                prompt = f"""Generate a short, casual message saying a game was skipped because it was too short (less than 1 minute). 
Include: opponent race ({opponent_race}), opponent name ({opponent_name}){map_part}.
Keep it brief and varied - don't use the exact same wording every time.
Examples: "Game skipped, too short vs {opponent_race} {opponent_name}{map_part}" or "Skipped {opponent_name}'s {opponent_race} game{map_part} - ended too quickly"
Generate ONE short message only, no explanation."""
                
                completion = send_prompt_to_openai(prompt)
                if completion and completion.choices and completion.choices[0].message:
                    skip_message = completion.choices[0].message.content.strip()
                else:
                    map_part = f" on {map_name}" if map_name != "Unknown" else ""
                    skip_message = f"Game skipped, too short vs {opponent_race} {opponent_name}{map_part}"
            except Exception as e:
                logger.error(f"Error generating skip message: {e}")
                map_part = f" on {map_name}" if map_name != "Unknown" else ""
                skip_message = f"Game skipped, too short vs {opponent_race} {opponent_name}{map_part}"
            
            for service in self.chat_services:
                try:
                    await service.send_message("chat", skip_message)
                except Exception as e:
                    logger.error(f"Error sending skip message to {service.get_platform_name()}: {e}")
            return
        
        # Announce Result
        try:
            from api.game_event_utils.game_ended_handler import game_ended
            
            game_player_names = ', '.join(game_info.get_player_names())
            winning_players = ', '.join(game_info.get_player_names(result_filter='Victory'))
            losing_players = ', '.join(game_info.get_player_names(result_filter='Defeat'))
            
            twitch_bot = None
            for service in self.chat_services:
                if hasattr(service, 'twitch_bot'):
                    twitch_bot = service.twitch_bot
                    break
            
            if twitch_bot:
                frames = replay_data.get('frames', 0)
                fps = replay_data.get('frames_per_second', 22.4)
                if fps > 0:
                    twitch_bot.total_seconds = frames / fps
                else:
                    twitch_bot.total_seconds = 0
                
                msg = await loop.run_in_executor(
                    None,
                    game_ended,
                    twitch_bot,
                    game_player_names,
                    winning_players,
                    losing_players,
                    logger
                )
                
                for service in self.chat_services:
                    try:
                        await service.send_message("channel", msg)
                    except Exception as e:
                        logger.error(f"Error sending announcement to service: {e}")
        except Exception as e:
            logger.error(f"Error generating game end announcement: {e}")
        
        # AI Commentary (skip if game too short or not 1v1)
        is_1v1_for_ai = game_info.total_players == 2
        if not is_too_short and not config.OPENAI_DISABLED and replay_data and is_1v1_for_ai:
            try:
                winning_players = ', '.join(game_info.get_player_names(result_filter='Victory'))
                losing_players = ', '.join(game_info.get_player_names(result_filter='Defeat'))
                
                frames = replay_data.get('frames', 0)
                fps = replay_data.get('frames_per_second', 22.4)
                duration_seconds = frames / fps if fps > 0 else 0
                duration_str = f"{int(duration_seconds // 60)}m {int(duration_seconds % 60)}s"
                
                concise_prompt = f"Provide ONE concise sentence (max 20 words) summarizing this StarCraft 2 game:\n\n"
                concise_prompt += f"Winner: {winning_players}\n"
                concise_prompt += f"Loser: {losing_players}\n"
                concise_prompt += f"Duration: {duration_str}\n"
                concise_prompt += f"Map: {replay_data.get('map', 'Unknown')}\n\n"
                concise_prompt += "Your ONE sentence summary:"
                
                twitch_bot = None
                for service in self.chat_services:
                    if hasattr(service, 'twitch_bot'):
                        twitch_bot = service.twitch_bot
                        break
                
                if twitch_bot:
                    from api.chat_utils import send_prompt_to_openai
                    completion = await loop.run_in_executor(None, send_prompt_to_openai, concise_prompt)
                    
                    if completion and completion.choices and completion.choices[0].message:
                        ai_commentary = completion.choices[0].message.content.strip()
                        for service in self.chat_services:
                            try:
                                await service.send_message("channel", ai_commentary)
                                logger.info(f"Sent AI commentary: {ai_commentary[:100]}")
                            except Exception as e:
                                logger.error(f"Error sending AI commentary: {e}")
            except Exception as e:
                logger.error(f"Error generating AI commentary: {e}")
        
        # Pattern Learning
        if not is_too_short and self.pattern_learner:
            total_players = game_info.total_players
            game_duration_seconds = game_info.displayTime
            
            is_1v1 = total_players == 2
            is_long_enough = game_duration_seconds >= config.ABANDONED_GAME_THRESHOLD
            
            streamer_played = False
            if replay_data and 'players' in replay_data:
                player_accounts_lower = [name.lower() for name in config.SC2_PLAYER_ACCOUNTS]
                for p_key, p_data in replay_data['players'].items():
                    if isinstance(p_data, dict) and p_data.get('name', '').lower() in player_accounts_lower:
                        streamer_played = True
                        break
            
            if is_1v1 and is_long_enough and streamer_played:
                async def delayed_learning_trigger():
                    logger.info(f"Pattern Learning: Waiting {config.PATTERN_LEARNING_DELAY_SECONDS}s before analysis...")
                    await asyncio.sleep(config.PATTERN_LEARNING_DELAY_SECONDS)
                    
                    try:
                        opponent_name = "Unknown"
                        opponent_race = "Unknown"
                        result = "Unknown"
                        
                        player_accounts_lower = [name.lower() for name in config.SC2_PLAYER_ACCOUNTS]
                        
                        for p_key, p_data in replay_data['players'].items():
                            if isinstance(p_data, dict):
                                name = p_data.get('name', '')
                                if name.lower() not in player_accounts_lower:
                                    opponent_name = name
                                    opponent_race = p_data.get('race', 'Unknown')
                                    if p_data.get('is_winner', False):
                                        result = "Defeat"
                                    else:
                                        result = "Victory"
                                    break
                        
                        # Extract opponent build order
                        build_order = []
                        for p_key, p_data in replay_data['players'].items():
                            if isinstance(p_data, dict) and p_data.get('name') == opponent_name:
                                build_order = p_data.get('buildOrder', [])
                                break
                        
                        game_data = {
                            'opponent_name': opponent_name,
                            'opponent_race': opponent_race,
                            'map': replay_data.get('map', 'Unknown'),
                            'date': replay_data.get('unix_timestamp', 0),
                            'result': result,
                            'duration': game_duration_seconds,
                            'build_order': build_order
                        }
                        
                        twitch_service = next((s for s in self.chat_services if s.get_platform_name() == 'twitch'), None)
                        if twitch_service and hasattr(twitch_service, 'twitch_bot'):
                            twitch_bot = twitch_service.twitch_bot
                            if hasattr(twitch_bot, '_display_pattern_validation'):
                                twitch_bot._display_pattern_validation(game_data, logger)
                            else:
                                prompt_msg = f"Game vs {opponent_name} ({opponent_race}) analyzed. Result: {result}. Type 'player comment <text>' to save notes."
                                await twitch_service.send_message("channel", prompt_msg)
                    except Exception as e:
                        logger.error(f"Pattern Learning Error: {e}")
                
                asyncio.create_task(delayed_learning_trigger())
        
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
        """
        Parse SC2 replay file using spawningtool.
        Wrapped in try/except to catch any exceptions, though segfaults will still crash.
        """
        try:
            # Additional validation before calling native library
            if not os.path.exists(path):
                raise FileNotFoundError(f"Replay file not found: {path}")
            
            if not os.access(path, os.R_OK):
                raise PermissionError(f"Cannot read replay file: {path}")
            
            # Call the parser (this may segfault on corrupted files)
            return spawningtool.parser.parse_replay(path)
        except Exception as e:
            logger.error(f"Exception in _parse_replay for {path}: {e}")
            raise
