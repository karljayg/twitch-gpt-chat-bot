import json
import requests
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
        try:
            response = requests.get("http://localhost:6119/game")
            response.raise_for_status()
            return GameInfo(response.json())
        except Exception as e:
            logger.debug(f"Is SC2 on? error: {e}")
            #return None
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

    previous_game = current_game
    if previous_game:
        logger.debug(f"GAME STATES (2): {previous_game}, {current_game.get_status()}, {previous_game.get_status()} \n")
    else:
        logger.debug(f"GAME STATES (3): {previous_game}, {current_game.get_status()}, {previous_game.get_status()} \n")

    response = ""
    replay_summary = ""

    logger.debug("The game status is " + current_game.get_status())
    game_player_names = ', '.join(current_game.get_player_names())
    winning_players = ', '.join(current_game.get_player_names(result_filter='Victory'))
    losing_players = ', '.join(current_game.get_player_names(result_filter='Defeat'))

    if current_game.get_status() in ("MATCH_ENDED", "REPLAY_ENDED"):
        if self.first_run:
            logger.debug("this is the first run")
            self.first_run = False
            if config.IGNORE_PREVIOUS_GAME_RESULTS_ON_FIRST_RUN:
                logger.debug("per config, ignoring previous game results on first run so no need to find latest replay file")
                return
        else:
            logger.debug("this is not first run")

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
            for player_key, player_data in replay_data['players'].items():
                if player_data['name'] in config.SC2_PLAYER_ACCOUNTS:
                    player_order.append(player_key)
                else:
                    opponent_name = player_data['name']
                    player_order.insert(0, player_key)

            for player_key in player_order:
                build_order = build_orders[player_key]
                player_info = f"{replay_data['players'][player_key]['name']}'s Build Order (first set of steps):"
                replay_summary += player_info + '\n'
                for order in build_order[:int(build_order_count)]:
                    time = order['time']
                    name = order['name']
                    supply = order['supply']
                    order_info = f"Time: {time}, Name: {name}, Supply: {supply}"
                    replay_summary += order_info + '\n'
                replay_summary += '\n'

            for player_name in config.SC2_PLAYER_ACCOUNTS:
                replay_summary = replay_summary.replace(player_name, config.STREAMER_NICKNAME)

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
        if hasattr(self, 'pattern_learner') and self.pattern_learner:
            logger.info("Pattern learning system found - scheduling delayed trigger")
            import threading
            import time
            
            def delayed_pattern_learning():
                logger.info("Starting delayed pattern learning trigger (15 second wait)")
                time.sleep(15)  # Wait 15 seconds for replay to be processed
                try:
                    logger.info("Delayed pattern learning trigger - checking if replay was saved")
                    
                    # Check if we have replay data available
                    if hasattr(self, 'last_replay_data') and self.last_replay_data:
                        logger.info("Replay data available - triggering pattern learning system")
                        
                        # Prepare game data for comment prompt
                        game_data = self._prepare_game_data_for_comment(game_player_names, winning_players, losing_players, logger)
                        logger.debug(f"Game data prepared for pattern learning: {game_data}")
                        
                        # Prompt for comment
                        logger.info("Prompting for player comment...")
                        comment = self.pattern_learner.prompt_for_player_comment(game_data)
                        
                        if comment:
                            logger.info(f"Player comment received: {comment}")
                        else:
                            # No comment provided - let AI learn from replay data
                            logger.info("No player comment - AI learning from replay data")
                            self.pattern_learner.process_game_without_comment(game_data)
                    else:
                        logger.warning("No replay data available after delay - pattern learning skipped")
                        logger.debug(f"Available attributes: {[attr for attr in dir(self) if not attr.startswith('_')]}")
                        
                except Exception as e:
                    logger.error(f"Error in delayed pattern learning: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Start the delayed trigger in a separate thread
            timer_thread = threading.Thread(target=delayed_pattern_learning, daemon=True)
            timer_thread.start()
            logger.info("Scheduled delayed pattern learning trigger (15 seconds)")
        else:
            logger.warning("Pattern learning system NOT available - check initialization")
            logger.debug(f"Available attributes: {[attr for attr in dir(self) if not attr.startswith('_')]}")

    elif current_game.get_status() == "REPLAY_STARTED":
        contextHistory.clear()
        response = f"{config.STREAMER_NICKNAME} is watching a replay of a game. The players are {game_player_names}"

    elif current_game.get_status() == "REPLAY_ENDED":
        response = game_replay_handler.replay_ended(self, current_game, game_player_names, logger)



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


def _prepare_game_data_for_comment(self, game_player_names, winning_players, losing_players, logger):
    """Prepare game data for the comment prompt"""
    try:
        game_data = {}
        
        # Get opponent info
        if config.STREAMER_NICKNAME in game_player_names:
            opponent_names = [name for name in game_player_names if name != config.STREAMER_NICKNAME]
            if opponent_names:
                game_data['opponent_name'] = opponent_names[0]
                
                # Try to get opponent race from current game
                try:
                    if hasattr(self, 'current_game') and self.current_game:
                        game_data['opponent_race'] = self.current_game.get_player_race(opponent_names[0])
                except:
                    game_data['opponent_race'] = 'Unknown'
        
        # Game result
        if config.STREAMER_NICKNAME in winning_players:
            game_data['result'] = 'Victory'
        elif config.STREAMER_NICKNAME in losing_players:
            game_data['result'] = 'Defeat'
        else:
            game_data['result'] = 'Tie'
        
        # Game duration
        if hasattr(self, 'total_seconds'):
            game_data['duration'] = f"{int(self.total_seconds // 60)}m {int(self.total_seconds % 60)}s"
        
        # Current date/time
        from datetime import datetime
        game_data['date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Map info (if available)
        try:
            if hasattr(self, 'last_replay_data') and self.last_replay_data:
                game_data['map'] = self.last_replay_data.get('map', 'Unknown')
            elif hasattr(self, 'current_game') and self.current_game:
                # This would need to be implemented based on your game data structure
                game_data['map'] = 'Unknown'
        except:
            game_data['map'] = 'Unknown'
        
        # Build order data (if available from replay data)
        try:
            # Check if we have replay data available
            if hasattr(self, 'last_replay_data') and self.last_replay_data:
                logger.debug(f"Replay data keys: {list(self.last_replay_data.keys())}")
                if 'players' in self.last_replay_data:
                    logger.debug(f"Players data: {self.last_replay_data['players']}")
                # Extract build order from replay data
                build_data = []
                if 'players' in self.last_replay_data:
                    for player in self.last_replay_data['players']:
                        if 'buildOrder' in player and isinstance(player['buildOrder'], list):
                            for step in player['buildOrder']:
                                if isinstance(step, dict):
                                    build_data.append({
                                        'supply': step.get('supply', 0),
                                        'name': step.get('name', ''),
                                        'time': step.get('time', 0)
                                    })
                        elif 'buildOrder' in player:
                            logger.debug(f"Build order is not a list: {type(player['buildOrder'])} - {player['buildOrder']}")
                
                if build_data:
                    game_data['build_order'] = build_data
                    logger.debug(f"Added {len(build_data)} build order steps to game data")
                else:
                    logger.debug("No build order data found in replay")
                    
        except Exception as e:
            logger.debug(f"Could not extract build order data: {e}")
        
        # Build order summary (if available)
        try:
            if hasattr(self, 'current_game') and self.current_game:
                # This would need to be implemented based on your game data structure
                game_data['build_order_summary'] = 'Not available'
        except:
            game_data['build_order_summary'] = 'Not available'
        
        return game_data
        
    except Exception as e:
        logger.error(f"Error preparing game data for comment: {e}")
        return {}