import json
import requests
import time
import utils.tokensArray as tokensArray
from utils.file_utils import find_latest_file
from utils.file_utils import find_recent_file_within_time
import spawningtool.parser
from api.game_event_utils import game_started_handler
from api.game_event_utils import game_replay_handler
from api.game_event_utils import game_ended_handler
from api.chat_utils import processMessageForOpenAI
from collections import defaultdict

from settings import config
from models.game_info import GameInfo

def reset_sc2_connection():
    """
    Force a fresh HTTP connection to SC2 API when stuck in bad state.
    
    This function is called after 5 consecutive SC2 API failures to attempt
    connection recovery. It tests multiple connection methods to find one that works:
    - localhost:6119 (standard local connection)
    - 127.0.0.1:6119 (IP-based connection, bypasses DNS resolution issues)
    
    The function uses completely fresh HTTP sessions to avoid cached connection
    pool issues that can cause the main requests to remain stuck even when
    the API is actually available.
    
    Returns:
        bool: True if reset successful and API is reachable, False if API is truly down
        
    Side Effects:
        - Updates reset_sc2_connection.working_url with the successful URL
        - Sets this URL to None if all connection methods fail
    """
    import time
    
    # Test URLs to try (localhost can sometimes have resolution issues)
    test_urls = [
        "http://localhost:6119/game",
        "http://127.0.0.1:6119/game"
    ]
    
    for url in test_urls:
        try:
            # Create completely fresh session (no connection pooling)
            # Use fresh request instead of session to avoid stale connections
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                    # Connection successful! Update the working URL for future use
                    reset_sc2_connection.working_url = url
                    return True
                
        except Exception:
            # This URL failed, try the next one
            continue
    
    # All connection methods failed
    reset_sc2_connection.working_url = None
    return False

# Store the working URL that reset found
reset_sc2_connection.working_url = None


@staticmethod
def check_SC2_game_status(logger):
    if config.TEST_MODE_SC2_CLIENT_JSON:
        try:
            with open(config.GAME_RESULT_TEST_FILE, 'r') as file:
                json_data = json.load(file)
            return GameInfo(json_data)
        except Exception as e:
            logger.debug(
                f"An error occurred while reading the test file: {e}")
            return None
    else:
        # Enhanced connection handling with health monitoring
        try:
            # Use configurable timeout to prevent hanging
            timeout = getattr(config, 'SC2_API_TIMEOUT_SECONDS', 10)
            
            # Use the working URL if reset found one, otherwise default to localhost
            url = getattr(reset_sc2_connection, 'working_url', None) or "http://localhost:6119/game"
            
            # Use fresh session if we just did a successful reset
            if hasattr(check_SC2_game_status, 'use_fresh_session') and check_SC2_game_status.use_fresh_session:
                response = requests.get(url, timeout=timeout)
                check_SC2_game_status.use_fresh_session = False  # Only use once
            else:
                response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            
            # Track successful connections
            if not hasattr(check_SC2_game_status, 'consecutive_successes'):
                check_SC2_game_status.consecutive_successes = 0
            check_SC2_game_status.consecutive_successes += 1
            
            # Reset failure counters on success
            if hasattr(check_SC2_game_status, 'consecutive_failures'):
                check_SC2_game_status.consecutive_failures = 0
            
            # Only log connection health at significant milestones (every 5000 polls = ~7 hours)
            # The visual indicators (., +, o, w) already show system health status
            if check_SC2_game_status.consecutive_successes % 5000 == 0:
                logger.debug(f"SC2 API connection healthy - {check_SC2_game_status.consecutive_successes} consecutive successful polls")
            
            return GameInfo(response.json())
            
        except requests.exceptions.Timeout:
            # Handle timeout specifically
            if not hasattr(check_SC2_game_status, 'consecutive_failures'):
                check_SC2_game_status.consecutive_failures = 0
            check_SC2_game_status.consecutive_failures += 1
            
            # Log full message on first timeout, then use visual indicators for repeats
            if check_SC2_game_status.consecutive_failures == 1:  # First timeout
                logger.debug(f"SC2 API timeout: request exceeded {getattr(config, 'SC2_API_TIMEOUT_SECONDS', 10)} seconds")
            elif check_SC2_game_status.consecutive_failures == 3:  # Escalate to warning after 3 timeouts
                logger.warning(f"SC2 API experiencing timeouts - {check_SC2_game_status.consecutive_failures} consecutive failures")
            elif check_SC2_game_status.consecutive_failures == 5:  # Try connection reset after 5 failures
                logger.info("Attempting SC2 API connection reset (timeouts)...")
                if reset_sc2_connection():
                    logger.info("SC2 API connection reset successful!")
                    check_SC2_game_status.consecutive_failures = 0  # Reset counter
                    check_SC2_game_status.use_fresh_session = True  # Use fresh session on next call
                    return check_SC2_game_status(logger)  # Retry immediately
                else:
                    logger.warning("SC2 API connection reset failed - API may be down")
            # All subsequent timeouts just use visual indicators (no log spam)
            
            return GameInfo({"status": "TIMEOUT"})
            
        except requests.exceptions.ConnectionError as e:
            # Handle connection errors specifically
            if not hasattr(check_SC2_game_status, 'consecutive_failures'):
                check_SC2_game_status.consecutive_failures = 0
            check_SC2_game_status.consecutive_failures += 1
            
            # Log full message on first failure, then use visual indicators for repeats
            if check_SC2_game_status.consecutive_failures == 1:  # First failure
                logger.debug(f"SC2 API connection error: {e}")
            elif check_SC2_game_status.consecutive_failures == 3:  # Escalate to warning after 3 failures
                logger.warning(f"SC2 API connection issues - {check_SC2_game_status.consecutive_failures} consecutive failures")
            elif check_SC2_game_status.consecutive_failures == 5:  # Try connection reset after 5 failures
                logger.info("Attempting SC2 API connection reset (connection errors)...")
                if reset_sc2_connection():
                    logger.info("SC2 API connection reset successful!")
                    check_SC2_game_status.consecutive_failures = 0  # Reset counter
                    check_SC2_game_status.use_fresh_session = True  # Use fresh session on next call
                    return check_SC2_game_status(logger)  # Retry immediately
                else:
                    logger.warning("SC2 API connection reset failed - API may be down")
            # All subsequent failures just use visual indicators (no log spam)
            
            return GameInfo({"status": "CONNECTION_ERROR"})
            
        except Exception as e:
            # Handle other errors
            if not hasattr(check_SC2_game_status, 'consecutive_failures'):
                check_SC2_game_status.consecutive_failures = 0
            check_SC2_game_status.consecutive_failures += 1
            
            # Log full message on first error, then use visual indicators for repeats
            if check_SC2_game_status.consecutive_failures == 1:  # First error
                logger.debug(f"SC2 API error: {e}")
            elif check_SC2_game_status.consecutive_failures == 3:  # Escalate to warning after 3 errors
                logger.warning(f"SC2 API experiencing errors - {check_SC2_game_status.consecutive_failures} consecutive failures")
            elif check_SC2_game_status.consecutive_failures == 5:  # Try connection reset after 5 failures
                logger.info("Attempting SC2 API connection reset...")
                if reset_sc2_connection():
                    logger.info("SC2 API connection reset successful!")
                    check_SC2_game_status.consecutive_failures = 0  # Reset counter
                    check_SC2_game_status.use_fresh_session = True  # Use fresh session on next call
                    return check_SC2_game_status(logger)  # Retry immediately
                else:
                    logger.warning("SC2 API connection reset failed - API may be down")
            # All subsequent errors just use visual indicators (no log spam)
            
            return GameInfo({"status": "ERROR"})

def handle_SC2_game_results(self, previous_game, current_game, contextHistory, logger):

    global consecutive_parse_failures
    consecutive_parse_failures = 0
    max_consecutive_parse_failures = 5

    # do not proceed if no change
    if previous_game and current_game.get_status() == previous_game.get_status():
        # when there is no change, no need to log so it does not repeat constantly
        # only turn on when there is an issue to debug
        # unlike below when there are changes, we always log
        # logger.debug(f"GAME STATES (1): {previous_game}, {current_game.get_status()}, {previous_game.get_status()} \n")
        return

    # CRITICAL: Capture the previous game state BEFORE overwriting it
    actual_previous_game = previous_game
    previous_game = current_game
    if previous_game:
        logger.debug(f"GAME STATES (2): {previous_game}, {current_game.get_status()}, {previous_game.get_status()}")
    else:
        logger.debug(f"GAME STATES (3): {previous_game}, {current_game.get_status()}, {previous_game.get_status()}")

    response = ""
    replay_summary = ""

    logger.debug("The game status is " + current_game.get_status())
    game_player_names = ', '.join(current_game.get_player_names())
    winning_players = ', '.join(current_game.get_player_names(result_filter='Victory'))
    losing_players = ', '.join(current_game.get_player_names(result_filter='Defeat'))

    if current_game.get_status() in ("MATCH_ENDED", "REPLAY_ENDED"):
        # Print indicator summary before processing game results
        try:
            from api.twitch_bot import _print_indicator_summary
            _print_indicator_summary()
        except:
            pass
            
        if self.first_run:
            logger.debug("this is the first run")
            self.first_run = False
            if config.IGNORE_PREVIOUS_GAME_RESULTS_ON_FIRST_RUN:
                logger.debug("per config, ignoring previous game results on first run so no need to find latest replay file")
                return
        else:
            logger.debug("this is not first run")

        # Wait for user to exit game/replay and for SC2 to finish writing replay file
        import time as time_mod
        time_mod.sleep(10)  # 10 second delay
        
        result = find_recent_file_within_time(
            config.REPLAYS_FOLDER,
            config.REPLAYS_FILE_EXTENSION,
            2,
            0,
            logger,
            self.last_replay_file
        )

        if self.last_replay_file == result:
            logger.debug(f"Skipping duplicate replay file: {result}")
            return

        if result:
            logger.debug(f"The path to the latest file is: {result}")
            if config.USE_CONFIG_TEST_REPLAY_FILE:
                result = config.REPLAY_TEST_FILE

            contextHistory.clear()

            # capture error so it does not run another processSC2game
            try:
                replay_data = spawningtool.parser.parse_replay(result)
                consecutive_parse_failures = 0
            except Exception as e:
                consecutive_parse_failures += 1
                logger.error(f"An error occurred while trying to parse the replay: {e}")
                if consecutive_parse_failures >= max_consecutive_parse_failures:
                    logger.error("Maximum number of consecutive parsing failures reached. Stopping the loop.")
                    return

            # Save the replay JSON to a file
            game_ended_handler.save_file(replay_data, 'json', logger)
            
            # Store replay data in the TwitchBot instance for pattern learning
            self.last_replay_data = replay_data

            # Players and Map
            players = [f"{player_data['name']}: {player_data['race']}" for player_data in
                        replay_data['players'].values()]
            region = replay_data['region']
            game_type = replay_data['game_type']
            unix_timestamp = replay_data['unix_timestamp']

            replay_summary += f"Players: {', '.join(players)}\n"
            replay_summary += f"Map: {replay_data['map']}\n"
            replay_summary += f"Region: {region}\n"
            replay_summary += f"Game Type: {game_type}\n"
            replay_summary += f"Timestamp: {unix_timestamp}\n"
            replay_summary += f"Winners: {winning_players}\n"
            replay_summary += f"Losers: {losing_players}\n"

            # Game Duration Calculations
            game_duration_result = game_ended_handler.calculate_game_duration(replay_data, logger)
            self.total_seconds = game_duration_result["totalSeconds"]
            replay_summary += f"Game Duration: {game_duration_result['gameDuration']}\n\n"

            # Total Players greater than 2, usually gets the total token size to 6k, and max is 4k so we divide by 2 to be safe
            if current_game.total_players > 2:
                build_order_count = config.BUILD_ORDER_COUNT_TO_ANALYZE / 2
            else:
                build_order_count = config.BUILD_ORDER_COUNT_TO_ANALYZE

            units_lost_summary = {player_key: player_data['unitsLost'] for player_key, player_data in replay_data['players'].items()}
            for player_key, units_lost in units_lost_summary.items():
                # ChatGPT gets confused if you use possessive 's vs by
                player_info = f"Units Lost by {replay_data['players'][player_key]['name']}"
                replay_summary += player_info + '\n'
                units_lost_aggregate = defaultdict(int)
                if units_lost:  # Check if units_lost is not empty
                    for unit in units_lost:
                        name = unit.get('name', "N/A")
                        units_lost_aggregate[name] += 1
                    for unit_name, count in units_lost_aggregate.items():
                        unit_info = f"{unit_name}: {count}"
                        replay_summary += unit_info + '\n'
                else:
                    replay_summary += "None \n"
                replay_summary += '\n'

            build_orders = {player_key: player_data['buildOrder'] for player_key, player_data in replay_data['players'].items()}
            opponent_name = None
            player_order = []
            # Create case-insensitive lookup
            player_accounts_lower = [name.lower() for name in config.SC2_PLAYER_ACCOUNTS]
            for player_key, player_data in replay_data['players'].items():
                if player_data['name'].lower() in player_accounts_lower:
                    player_order.append(player_key)
                else:
                    opponent_name = player_data['name']
                    player_order.insert(0, player_key)

            for player_key in player_order:
                build_order = build_orders[player_key]
                player_info = f"{replay_data['players'][player_key]['name']}'s Build Order (first set of steps):"
                replay_summary += player_info + '\n'
                for order in build_order[:int(build_order_count)]:
                    order_time = order['time']
                    name = order['name']
                    supply = order['supply']
                    order_info = f"Time: {order_time}, Name: {name}, Supply: {supply}"
                    replay_summary += order_info + '\n'
                replay_summary += '\n'

            # Replace all player account names (case-insensitive) with STREAMER_NICKNAME
            for player_name in config.SC2_PLAYER_ACCOUNTS:
                # Use case-insensitive replacement by creating a pattern
                import re
                pattern = re.compile(re.escape(player_name), re.IGNORECASE)
                replay_summary = pattern.sub(config.STREAMER_NICKNAME, replay_summary)

            game_ended_handler.save_file(replay_summary, 'summary', logger)

            try:
                if self.db.insert_replay_info(replay_summary):
                    logger.debug("replay summary saved to database")
                else:
                    logger.debug("replay summary not saved to database")
            except Exception as e:
                logger.debug(f"error with database: {e}")

        else:
            logger.debug("No result found!")

    if current_game.get_status() == "MATCH_STARTED":
        game_player_names = game_started_handler.game_started(self, current_game, contextHistory, logger)

    elif current_game.get_status() == "MATCH_ENDED":
        response = game_ended_handler.game_ended(self, game_player_names, winning_players, losing_players, logger)
        
        # Schedule pattern learning trigger after a delay to allow replay processing
        # Note: Due to Blizzard API bug (isReplay always "true"), we now detect real games
        # by checking if streamer is playing, not by the broken isReplay flag
        # Only trigger pattern learning for 1v1 games that weren't abandoned
        if (hasattr(self, 'pattern_learner') and self.pattern_learner and 
            hasattr(self, 'total_seconds') and self.total_seconds >= config.ABANDONED_GAME_THRESHOLD and
            current_game.total_players == 2):  # Only 1v1 games
            logger.info("Pattern learning system found - scheduling delayed trigger (1v1 game)")
            import threading
            
            def delayed_pattern_learning(captured_game_player_names, captured_winning_players, captured_losing_players):
                logger.info(f"Starting delayed pattern learning trigger ({config.PATTERN_LEARNING_DELAY_SECONDS} second wait)")
                time.sleep(config.PATTERN_LEARNING_DELAY_SECONDS)  # Wait for replay to be processed
                try:
                    # Check if we have replay data available
                    if hasattr(self, 'last_replay_data') and self.last_replay_data:
                        logger.info("Replay data available - triggering pattern learning system")
                        
                        # Prepare game data for comment prompt
                        logger.debug(f"DEBUG: captured_game_player_names before _prepare_game_data_for_comment: {repr(captured_game_player_names)}")
                        game_data = self._prepare_game_data_for_comment(captured_game_player_names, captured_winning_players, captured_losing_players, logger)
                        logger.debug(f"Game data prepared for pattern learning: {game_data}")
                        
                        # ALWAYS display pattern validation (read-only, safe to show even during replay)
                        self._display_pattern_validation(game_data, logger)
                        
                        # Now check game state for prompt availability
                        logger.info("Delayed pattern learning trigger - checking if safe to prompt")
                        try:
                            current_game_status = check_SC2_game_status(logger)
                            if current_game_status:
                                current_status = current_game_status.get_status()
                                
                                # Skip if watching replay - REPLAY_ENDED will trigger fresh prompt with full timeout
                                if current_status == "REPLAY_STARTED":
                                    logger.info("Player watching replay - deferring prompt until replay ends")
                                    return  # Game stays unprocessed, REPLAY_ENDED will prompt again
                                
                                # Skip if started new match - player has moved on
                                if current_status == "MATCH_STARTED":
                                    logger.info("Player started new game - skipping prompt (game remains unprocessed for manual comment later)")
                                    return
                                    
                                logger.debug(f"Game state: {current_status} - proceeding with prompt")
                        except Exception as e:
                            logger.warning(f"Could not check game state: {e} - proceeding with prompt anyway")
                        
                        # Player comments now handled via Twitch chat using "player comment <text>"
                        # No console prompt needed - user will type in Twitch chat when ready
                        logger.info("Game data prepared - player can add comment via Twitch chat: 'player comment <text>'")
                    else:
                        logger.warning("No replay data available after delay - pattern learning skipped")
                        logger.debug(f"Available attributes: {[attr for attr in dir(self) if not attr.startswith('_')]}")
                        
                except Exception as e:
                    logger.error(f"Error in delayed pattern learning: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Start the delayed trigger in a separate thread with captured variables
            timer_thread = threading.Thread(target=delayed_pattern_learning, args=(game_player_names, winning_players, losing_players), daemon=True)
            timer_thread.start()
            logger.info(f"Scheduled delayed pattern learning trigger ({config.PATTERN_LEARNING_DELAY_SECONDS} seconds)")
        elif current_game.total_players != 2:
            logger.info(f"Skipping pattern learning for non-1v1 game ({current_game.total_players} players - team game)")
        elif hasattr(self, 'total_seconds') and self.total_seconds < config.ABANDONED_GAME_THRESHOLD:
            logger.info(f"Skipping pattern learning for short game ({self.total_seconds}s < {config.ABANDONED_GAME_THRESHOLD}s threshold)")
        else:
            logger.warning("Pattern learning system NOT available - check initialization")
            logger.debug(f"Available attributes: {[attr for attr in dir(self) if not attr.startswith('_')]}")

    elif current_game.get_status() == "REPLAY_STARTED":
        contextHistory.clear()
        response = f"{config.STREAMER_NICKNAME} is watching a replay of a game. The players are {game_player_names}"

    elif current_game.get_status() == "REPLAY_ENDED":
        response = game_replay_handler.replay_ended(self, current_game, game_player_names, logger)
        
        # SIMPLE AND CORRECT: Only trigger pattern learning if we did NOT start with REPLAY_STARTED
        # If previous state was REPLAY_STARTED, then this is just watching a replay - skip learning
        # If previous state was anything else (MATCH_STARTED, etc), then this is a live game ending - do learning
        previous_status = actual_previous_game.get_status() if (actual_previous_game and hasattr(actual_previous_game, 'get_status')) else "None"
        logger.debug(f"REPLAY_ENDED: previous state was {previous_status}")
        
        player_names_list = [name.strip() for name in game_player_names.split(',')]
        player_accounts_lower = [name.lower() for name in config.SC2_PLAYER_ACCOUNTS]
        streamer_is_playing = any(name.lower() in player_accounts_lower for name in player_names_list)
        
        # Only trigger if: 1) You're in the game AND 2) Previous state was NOT REPLAY_STARTED AND 3) Game wasn't abandoned AND 4) It's a 1v1 game
        if (hasattr(self, 'pattern_learner') and self.pattern_learner and streamer_is_playing and 
            previous_status != "REPLAY_STARTED" and 
            hasattr(self, 'total_seconds') and self.total_seconds >= config.ABANDONED_GAME_THRESHOLD and
            current_game.total_players == 2):  # Only 1v1 games
            logger.info(f"REPLAY_ENDED: Live 1v1 game ended (was {previous_status}) - triggering pattern learning")
            
            import threading
            
            def delayed_pattern_learning(captured_game_player_names, captured_winning_players, captured_losing_players):
                logger.info(f"Starting delayed pattern learning trigger ({config.PATTERN_LEARNING_DELAY_SECONDS} second wait)")
                time.sleep(config.PATTERN_LEARNING_DELAY_SECONDS)  # Wait for replay to be processed
                try:
                    # Check if we have replay data available
                    if hasattr(self, 'last_replay_data') and self.last_replay_data:
                        logger.info("Replay data available - triggering pattern learning system")
                        
                        # Prepare game data for comment prompt
                        game_data = self._prepare_game_data_for_comment(captured_game_player_names, captured_winning_players, captured_losing_players, logger)
                        logger.debug(f"Game data prepared for pattern learning: {game_data}")
                        
                        # ALWAYS display pattern validation (read-only, safe to show even during replay)
                        self._display_pattern_validation(game_data, logger)
                        
                        # Now check game state for prompt availability
                        logger.info("Delayed pattern learning trigger - checking if safe to prompt")
                        try:
                            current_game_status = check_SC2_game_status(logger)
                            if current_game_status:
                                current_status = current_game_status.get_status()
                                
                                # Skip if watching replay - REPLAY_ENDED will trigger fresh prompt with full timeout
                                if current_status == "REPLAY_STARTED":
                                    logger.info("Player watching replay - deferring prompt until replay ends")
                                    return  # Game stays unprocessed, REPLAY_ENDED will prompt again
                                
                                # Skip if started new match - player has moved on
                                if current_status == "MATCH_STARTED":
                                    logger.info("Player started new game - skipping prompt (game remains unprocessed for manual comment later)")
                                    return
                                    
                                logger.debug(f"Game state: {current_status} - proceeding with prompt")
                        except Exception as e:
                            logger.warning(f"Could not check game state: {e} - proceeding with prompt anyway")
                        
                        # Player comments now handled via Twitch chat using "player comment <text>"
                        # No console prompt needed - user will type in Twitch chat when ready
                        logger.info("Game data prepared - player can add comment via Twitch chat: 'player comment <text>'")
                    else:
                        logger.warning("No replay data available after delay - pattern learning skipped")
                        
                except Exception as e:
                    logger.error(f"Error in delayed pattern learning: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Start the delayed trigger in a separate thread with captured variables
            timer_thread = threading.Thread(target=delayed_pattern_learning, args=(game_player_names, winning_players, losing_players), daemon=True)
            timer_thread.start()
            logger.info(f"Scheduled delayed pattern learning trigger ({config.PATTERN_LEARNING_DELAY_SECONDS} seconds)")
        else:
            if previous_status == "REPLAY_STARTED":
                logger.debug("Pattern learning skipped: watching replay (REPLAY_STARTED to REPLAY_ENDED)")
            elif current_game.total_players != 2:
                logger.info(f"Skipping pattern learning for non-1v1 game ({current_game.total_players} players - team game)")
            elif hasattr(self, 'total_seconds') and self.total_seconds < config.ABANDONED_GAME_THRESHOLD:
                logger.info(f"Skipping pattern learning for short game ({self.total_seconds}s < {config.ABANDONED_GAME_THRESHOLD}s threshold)")
            else:
                logger.debug("Pattern learning not triggered: not streamer's game or system unavailable")



    if not config.OPENAI_DISABLED:
        if self.first_run:
            logger.debug("this is the first run")
            self.first_run = False
            if config.IGNORE_PREVIOUS_GAME_RESULTS_ON_FIRST_RUN:
                logger.debug("per config, ignoring previous game results on first run")
                return

        logger.debug("current game status: " + current_game.get_status() +
                     " isReplay: " + str(current_game.isReplay) +
                     " ANALYZE_REPLAYS_FOR_TEST: " + str(config.USE_CONFIG_TEST_REPLAY_FILE))

        if ((current_game.get_status() not in ["MATCH_STARTED", "REPLAY_STARTED"] and self.total_seconds >= config.ABANDONED_GAME_THRESHOLD)
                or (current_game.isReplay and config.USE_CONFIG_TEST_REPLAY_FILE)):
            logger.debug("analyzing, replay summary to AI: ")
            processMessageForOpenAI(self, replay_summary, "replay_analysis", logger, contextHistory)
            replay_summary = ""
        else:
            logger.debug("not analyzing replay")
            return

