import json
import requests
from utils.file_utils import find_latest_file
import spawningtool.parser
from .game_event_utils import game_started_handler
from .game_event_utils import game_replay_handler
from .game_event_utils import game_ended_handler
from .chat_utils import processMessageForOpenAI
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
            return None

def handle_SC2_game_results(self, previous_game, current_game, contextHistory, logger):
    # do not proceed if no change
    if previous_game and current_game.get_status() == previous_game.get_status():
        # TODO: hide logger after testing
        # logger.debug("previous game status: " + str(previous_game.get_status()) + " current game status: " + str(current_game.get_status()))
        return
    else:
        # do this here also, to ensure it does not get processed again
        previous_game = current_game
        if previous_game:
            pass
            # logger.debug("previous game status: " + str(previous_game.get_status()) + " current game status: " + str(current_game.get_status()))
        else:
            # logger.debug("previous game status: (assumed None) current game status: " + str(current_game.get_status()))
            pass
    
    response = ""
    replay_summary = ""  # Initialize summary string

    logger.debug("The game status is " + current_game.get_status())

    # prevent the array brackets from being included
    game_player_names = ', '.join(current_game.get_player_names())

    winning_players = ', '.join(
        current_game.get_player_names(result_filter='Victory'))
    
    losing_players = ', '.join(
        current_game.get_player_names(result_filter='Defeat'))
    
    if current_game.get_status() in ("MATCH_ENDED", "REPLAY_ENDED"):
        result = find_latest_file(config.REPLAYS_FOLDER, config.REPLAYS_FILE_EXTENSION, logger)
        
        # there are times when current replay file is not ready and it still finds the prev. one despite the SLEEP TIMEOUT of 7 secs
        # so we are going to do this also to prevent the bot from commenting on the same replay file as the last one
        if self.last_replay_file == result:
            logger.debug("last replay file is same as current, skipping: \n" + result)
            return

        if result:
            logger.debug(f"The path to the latest file is: {result}")
            if config.USE_CONFIG_TEST_REPLAY_FILE:
                # use the config test file instead of latest found dynamically
                result = config.REPLAY_TEST_FILE

            # clear context history since replay analysis takes most of the tokens allowed
            # print(', '.join(map(str, contextHistory)))
            contextHistory.clear()

            # capture error so it does not run another processSC2game
            try:
                replay_data = spawningtool.parser.parse_replay(result)
            except Exception as e:
                logger.error(
                    f"An error occurred while trying to parse the replay: {e}")

            # Save the replay JSON to a file
            game_ended_handler.save_file(replay_data, 'json', logger)

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

            #################################
            # Units Lost
            units_lost_summary = {player_key: player_data['unitsLost'] for player_key, player_data in
                                    replay_data['players'].items()}
            
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

            # Build Orders
            build_orders = {player_key: player_data['buildOrder'] for player_key, player_data in
                            replay_data['players'].items()}

            # Separate players based on SC2_PLAYER_ACCOUNTS, start with opponent first
            player_order = []
            for player_key, player_data in replay_data['players'].items():
                if player_data['name'] in config.SC2_PLAYER_ACCOUNTS:
                    player_order.append(player_key)
                else:
                    # Put opponent at the start
                    player_order.insert(0, player_key)

            # Loop through build orders using the modified order
            for player_key in player_order:
                build_order = build_orders[player_key]
                player_info = f"{replay_data['players'][player_key]['name']}'s Build Order (first 20 steps):"
                replay_summary += player_info + '\n'
                for order in build_order[:int(build_order_count)]:
                    time = order['time']
                    name = order['name']
                    supply = order['supply']
                    order_info = f"Time: {time}, Name: {name}, Supply: {supply}"
                    replay_summary += order_info + '\n'
                replay_summary += '\n'

            # replace player names with streamer name
            for player_name in config.SC2_PLAYER_ACCOUNTS:
                replay_summary = replay_summary.replace(
                    player_name, config.STREAMER_NICKNAME)

            # Save the replay summary to a file
            game_ended_handler.save_file(replay_summary, 'summary', logger)

            # Save to the database
            try:
                if self.db.insert_replay_info(replay_summary):
                    logger.debug("replay summary saved to database")
                else:
                    logger.debug("replay summary not saved to database")
            except Exception as e:
                logger.debug(f"error with database: {e}")

        else:
            logger.debug("No result found!")

################

    if current_game.get_status() == "MATCH_STARTED":
        # check to see if player exists in database
        game_player_names = game_started_handler.game_started(self, current_game, contextHistory, logger)

    elif current_game.get_status() == "MATCH_ENDED":
        response = game_ended_handler.game_ended(self, game_player_names,winning_players,losing_players, logger)

    elif current_game.get_status() == "REPLAY_STARTED":
        # no game intros during replays
        # self.play_SC2_sound("start")
        # clear context history so that the bot doesn't mix up results from previous games
        contextHistory.clear()
        response = f"{config.STREAMER_NICKNAME} is watching a replay of a game. The players are {game_player_names}"

    elif current_game.get_status() == "REPLAY_ENDED":
        response = game_replay_handler.replay_ended(self, current_game, game_player_names, logger)

    if not config.OPENAI_DISABLED:
        if self.first_run:
            logger.debug("this is the first run")
            self.first_run = False
            if config.IGNORE_PREVIOUS_GAME_RESULTS_ON_FIRST_RUN:
                logger.debug(
                    "per config, ignoring previous game results on first run")
                return # exit function, do not proceed to comment on the result, and analysis on game summary
        else:
            logger.debug("this is not first run")

        # proceed
        # processMessageForOpenAI(self, response, self.conversation_mode, logger, contextHistory)

        # get analysis of game summary from the last real game's replay file that created, unless using config test replay file
        logger.debug("current game status: " + current_game.get_status() +
                        " isReplay: " + str(current_game.isReplay) +
                        " ANALYZE_REPLAYS_FOR_TEST: " + str(config.USE_CONFIG_TEST_REPLAY_FILE))

        # we do not want to analyze when the game (live or replay) is not in an ended state
        # or if the duration is short (abandoned game)
        # unless we are testing with a replay file
        if ((current_game.get_status() not in ["MATCH_STARTED", "REPLAY_STARTED"] and self.total_seconds >= config.ABANDONED_GAME_THRESHOLD)
                or (current_game.isReplay and config.USE_CONFIG_TEST_REPLAY_FILE)):
            # get analysis of ended games, or during testing of config test replay file
            logger.debug("analyzing, replay summary to AI: ")
            processMessageForOpenAI(self, replay_summary, "replay_analysis", logger, contextHistory)
            # clear after analyzing and making a comment
            replay_summary = ""
        else:
            logger.debug("not analyzing replay")
            return