import irc.bot
import openai
import json
import random
import time
import urllib3
import threading
import signal
import sys
import logging
import math
import spawningtool.parser
import tiktoken
import pytz
from datetime import datetime
from collections import defaultdict

from settings import config
import utils.tokensArray as tokensArray
import utils.wiki_utils as wiki_utils
from models.mathison_db import Database
from models.log_once_within_interval_filter import LogOnceWithinIntervalFilter
from utils.emote_utils import get_random_emote
from utils.file_utils import find_latest_file
from utils.sound_player_utils import SoundPlayer
from .sc2_game_utils import check_SC2_game_status
from .chat_utils import message_on_welcome, process_pubmsg, processMessageForOpenAI

# The contextHistory array is a list of tuples, where each tuple contains two elements: the message string and its
# corresponding token size. This allows us to keep track of both the message content and its size in the array. When
# a new message is added to the contextHistory array, its token size is determined using the nltk.word_tokenize()
# function. If the total number of tokens in the array exceeds the maxContextTokens threshold, the function starts
# deleting items from the end of the array until the total number of tokens is below the threshold. If the last item
# in the array has a token size less than or equal to the maxContextTokens threshold, the item is removed completely.
# However, if the last item has a token size greater than the threshold, the function removes tokens from the end of
# the message string until its token size is less than or equal to the threshold, and keeps the shortened message
# string in the array. If the total number of tokens in the array is still above the threshold after deleting the
# last item, the function repeats the process with the second-to-last item in the array, and continues deleting items
# until the total number of tokens is below the threshold. By using this logic, we can ensure that the contextHistory
# array always contains a maximum number of tokens specified by maxContextTokens, while keeping the most recent
# messages in the array.
global contextHistory
contextHistory = []


# Initialize the logger at the beginning of the script
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addFilter(LogOnceWithinIntervalFilter())

# Set logging level for urllib3 to WARNING
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

# Player names of streamer to check results for
player_names = config.SC2_PLAYER_ACCOUNTS


class TwitchBot(irc.bot.SingleServerIRCBot):
    def __init__(self):
        self.first_run = True
        self.last_replay_file = None
        self.conversation_mode = "normal"
        self.total_seconds = 0
        self.encoding = tiktoken.get_encoding(config.TOKENIZER_ENCODING)
        self.encoding = tiktoken.encoding_for_model(config.ENGINE)

        # handle KeyboardInterrupt in a more graceful way by setting a flag when Ctrl-C is pressed and checking that
        # flag in threads that need to be terminated
        self.shutdown_flag = False
        signal.signal(signal.SIGINT, self.signal_handler)

        # threads to be terminated as soon as the main program finishes when set as daemon threads
        monitor_thread = threading.Thread(target=self.monitor_game)
        monitor_thread.daemon = True
        monitor_thread.start()

        # Generate the current datetime timestamp in the format YYYYMMDD-HHMMSS
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        # Append the timestamp to the log file name
        log_file_name = config.LOG_FILE.replace(".log", f"_{timestamp}.log")
        # Set up the logging configuration
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            '%(asctime)s:%(levelname)s:%(name)s: %(message)s')
        file_handler = logging.FileHandler(log_file_name)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Set bot configuration
        self.token = config.TOKEN
        self.channel = config.CHANNEL
        self.username = config.USERNAME
        self.server = config.HOST
        self.port = config.PORT
        self.ignore = config.IGNORE
        openai.api_key = config.OPENAI_API_KEY

        self.streamer_nickname = config.STREAMER_NICKNAME
        self.selected_moods = [config.MOOD_OPTIONS[i]
                               for i in config.BOT_MOODS]
        self.selected_perspectives = [
            config.PERSPECTIVE_OPTIONS[i] for i in config.BOT_PERSPECTIVES]

        # Initialize the IRC bot
        irc.bot.SingleServerIRCBot.__init__(self, [(self.server, self.port, 'oauth:' + self.token)], self.username,
                                            self.username)
        # # SC2 sounds
        self.sound_player = SoundPlayer()

        # Initialize the database
        self.db = Database()

    def play_SC2_sound(self, game_event):
        if config.PLAYER_INTROS_ENABLED:
            if config.IGNORE_PREVIOUS_GAME_RESULTS_ON_FIRST_RUN and self.first_run:
                logger.debug(
                    "Per config, ignoring previous game on the first run, so no sound will be played")
                return
            self.sound_player.play_sound(game_event)
        else:
            logger.debug("SC2 player intros and other sounds are disabled")

    # incorrect IDE warning here, keep parameters at 3
    def signal_handler(self, signal, frame):
        self.shutdown_flag = True
        logger.debug(
            "================================================SHUTTING DOWN BOT========================================")
        self.die("Shutdown requested.")
        sys.exit(0)

    def handle_SC2_game_results(self, previous_game, current_game):

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

        logger.debug("game status is " + current_game.get_status())

        # prevent the array brackets from being included
        game_player_names = ', '.join(current_game.get_player_names())

        winning_players = ', '.join(
            current_game.get_player_names(result_filter='Victory'))
        losing_players = ', '.join(
            current_game.get_player_names(result_filter='Defeat'))

        if current_game.get_status() in ("MATCH_ENDED", "REPLAY_ENDED"):

            result = find_latest_file(
                config.REPLAYS_FOLDER, config.REPLAYS_FILE_EXTENSION, logger)
            # there are times when current replay file is not ready and it still finds the prev. one despite the SLEEP TIMEOUT of 7 secs
            # so we are going to do this also to prevent the bot from commenting on the same replay file as the last one
            if (self.last_replay_file == result):
                logger.debug(
                    "last replay file is same as current, skipping: \n" + result)
                return

            if result:
                logger.debug(f"The path to the latest file is: {result}")

                if config.USE_CONFIG_TEST_REPLAY_FILE:
                    # use the config test file instead of latest found dynamically
                    result = config.REPLAY_TEST_FILE

                # clear context history since replay analysis takes most of the tokens allowed
                contextHistory.clear()

                # capture error so it does not run another processSC2game
                try:
                    replay_data = spawningtool.parser.parse_replay(result)
                except Exception as e:
                    logger.error(
                        f"An error occurred while trying to parse the replay: {e}")

                # Save the replay JSON to a file
                filename = config.LAST_REPLAY_JSON_FILE
                with open(filename, 'w') as file:
                    json.dump(replay_data, file, indent=4)
                    logger.debug('last replay file saved: ' + filename)

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

                # Game Duration
                frames = replay_data['frames']
                frames_per_second = replay_data['frames_per_second']

                self.total_seconds = frames / frames_per_second
                minutes = int(self.total_seconds // 60)
                seconds = int(self.total_seconds % 60)

                game_duration = f"{minutes}m {seconds}s"
                replay_summary += f"Game Duration: {game_duration}\n\n"
                logger.debug(f"Game Duration: {game_duration}")

                # Total Players greater than 2, usually gets the total token size to 6k, and max is 4k so we divide by 2 to be safe
                if current_game.total_players > 2:
                    build_order_count = config.BUILD_ORDER_COUNT_TO_ANALYZE / 2
                else:
                    build_order_count = config.BUILD_ORDER_COUNT_TO_ANALYZE

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
                filename = config.LAST_REPLAY_SUMMARY_FILE
                with open(filename, 'w') as file:
                    file.write(replay_summary)
                    logger.debug('last replay summary saved: ' + filename)

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

        if current_game.get_status() == "MATCH_STARTED":
            # check to see if player exists in database
            try:
                # if game_type == "1v1":
                if current_game.total_players == 2:
                    logger.debug(
                        "1v1 game, so checking if player exists in database")
                    game_player_names = [name.strip()
                                         for name in game_player_names.split(',')]
                    for player_name in game_player_names:
                        logger.debug(f"looking for: {player_name}")
                        if player_name != config.STREAMER_NICKNAME:
                            result = self.db.check_player_exists(
                                player_name, current_game.get_player_race(player_name))
                            if result is not None:

                                # Set the timezone for Eastern Time
                                eastern = pytz.timezone('US/Eastern')

                                # already in Eastern Time since it is using DB replay table Date_Played column
                                date_obj = eastern.localize(
                                    result['Date_Played'])

                                # Get the current datetime in Eastern Time
                                current_time_eastern = datetime.now(eastern)

                                # Calculate the difference
                                delta = current_time_eastern - date_obj

                                # Extract the number of days
                                days_ago = delta.days
                                hours_ago = delta.seconds // 3600
                                seconds_ago = delta.seconds

                                # Determine the appropriate message
                                if days_ago == 0:
                                    mins_ago = seconds_ago // 60
                                    if mins_ago > 60:
                                        how_long_ago = f"{hours_ago} hours ago."
                                    else:
                                        how_long_ago = f"{mins_ago} seconds ago."
                                else:
                                    how_long_ago = f"{days_ago} days ago"

                                first_30_build_steps = self.db.extract_opponent_build_order(
                                    player_name)

                                msg = "Do both: \n"
                                msg += f"Mention all details here: {config.STREAMER_NICKNAME} played {player_name} {how_long_ago} in {{Map name}},"
                                msg += f"and the result was a {{Win/Loss for {config.STREAMER_NICKNAME}}} in {{game duration}}. \n"
                                msg += f"As a StarCraft 2 expert, comment on last game summary. Be concise with only 2 sentences total of 25 words or less. \n"
                                msg += "-----\n"
                                msg += f"last game summary: \n {result['Replay_Summary']} \n"
                                #self.processMessageForOpenAI(msg, "last_time_played")
                                processMessageForOpenAI(self, msg, "last_time_played", logger, contextHistory)

                                msg = f"Do both: \n"
                                msg += "First, print the build order exactly as shown. \n"
                                msg += "After, summarize the build order 7 words or less. \n"
                                msg += "-----\n"
                                msg += f"{first_30_build_steps} \n"
                                #self.processMessageForOpenAI(msg, "last_time_played")
                                processMessageForOpenAI(self, msg, "last_time_played", logger, contextHistory)

                            else:
                                msg = "Restate this without missing any details: \n "
                                msg += f"I think this is the first time {config.STREAMER_NICKNAME} is playing {player_name}, at least the {current_game.get_player_race(player_name)} of {player_name}"
                                logger.debug(msg)
                                #self.processMessageForOpenAI(msg, "in_game")
                                processMessageForOpenAI(self, msg, "in_game", logger, contextHistory)
                            break  # avoid processingMessageForOpenAI again below

            except Exception as e:
                logger.debug(f"error with find if player exists: {e}")

        elif current_game.get_status() == "MATCH_ENDED":
            if len(winning_players) == 0:
                response = f"Game with {game_player_names} ended with a Tie!"
                self.play_SC2_sound("tie")

            else:
                # Compare with the threshold
                if self.total_seconds < config.ABANDONED_GAME_THRESHOLD:
                    logger.debug("Game duration is less than " +
                                 str(config.ABANDONED_GAME_THRESHOLD) + " seconds.")
                    response = f"The game was abandoned immediately in just {self.total_seconds} seconds between {game_player_names} and so {winning_players} get the free win."
                    self.play_SC2_sound("abandoned")
                else:
                    response = f"Game with {game_player_names} ended with {winning_players} beating {losing_players}"
                    if config.STREAMER_NICKNAME in winning_players:
                        self.play_SC2_sound("victory")
                    else:
                        self.play_SC2_sound("defeat")

        elif current_game.get_status() == "REPLAY_STARTED":
            self.play_SC2_sound("start")
            # clear context history so that the bot doesn't mix up results from previous games
            contextHistory.clear()
            response = f"{config.STREAMER_NICKNAME} is watching a replay of a game. The players are {game_player_names}"

        elif current_game.get_status() == "REPLAY_ENDED":
            winning_players = ', '.join(
                current_game.get_player_names(result_filter='Victory'))
            losing_players = ', '.join(
                current_game.get_player_names(result_filter='Defeat'))

            if len(winning_players) == 0:
                response = f"The game with {game_player_names} ended with a Tie!"
            else:

                # Compare with the threshold
                if self.total_seconds < config.ABANDONED_GAME_THRESHOLD:
                    response = f"This was an abandoned game where duration was just {self.total_seconds} seconds between {game_player_names} and so {winning_players} get the free win."
                    logger.debug(response)
                    self.play_SC2_sound("abandoned")
                else:
                    if config.STREAMER_NICKNAME in winning_players:
                        self.play_SC2_sound("victory")
                    else:
                        self.play_SC2_sound("defeat")
                    response = (f"The game with {game_player_names} ended in a win for "
                                f"{winning_players} and a loss for {losing_players}")

        if not config.OPENAI_DISABLED:
            if self.first_run:
                logger.debug("this is the first run")
                self.first_run = False
                if config.IGNORE_PREVIOUS_GAME_RESULTS_ON_FIRST_RUN:
                    logger.debug(
                        "per config, ignoring previous game results on first run")
                    return  # exit function, do not proceed to comment on the result, and analysis on game summary
            else:
                logger.debug("this is not first run")

            # proceed
            #self.processMessageForOpenAI(response, self.conversation_mode)
            processMessageForOpenAI(self, response, self.conversation_mode, logger, contextHistory)

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
                #self.processMessageForOpenAI(replay_summary, "replay_analysis")
                processMessageForOpenAI(self, replay_summary, "replay_analysis", logger, contextHistory)
                # clear after analyzing and making a comment
                replay_summary = ""
            else:
                logger.debug("not analyzing replay")
                return

    def monitor_game(self):
        previous_game = None

        while True and not self.shutdown_flag:
            try:
                current_game = check_SC2_game_status()
                if (current_game.get_status() == "MATCH_STARTED" or current_game.get_status() == "REPLAY_STARTED"):
                    self.conversation_mode = "in_game"
                else:
                    self.conversation = "normal"
                if current_game:
                    if config.IGNORE_GAME_STATUS_WHILE_WATCHING_REPLAYS and current_game.isReplay:
                        pass
                    else:
                        # wait so abandoned games doesnt result in false data of 0 seconds
                        time.sleep(2)
                        self.handle_SC2_game_results(
                            previous_game, current_game)

                previous_game = current_game
                time.sleep(config.MONITOR_GAME_SLEEP_SECONDS)
                # heartbeat indicator
                print(".", end="", flush=True)
            except Exception as e:
                pass

    # This is a callback method that is invoked when bot successfully connects to an IRC Server
    def on_welcome(self, connection, event):
        # Join the channel and say a greeting
        connection.join(self.channel)
        message_on_welcome(self, logger)

    # This function is a listerner whenever there is a publish message on twitch chat room
    def on_pubmsg(self, connection, event):
        
        #process the message sent by the viewers in the twitch chat room
        process_pubmsg(self, event, logger, contextHistory)