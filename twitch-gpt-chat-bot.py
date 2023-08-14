import irc.bot
import openai
import re
import tokensArray
import asyncio
import json
import random
import time
import urllib3
import threading
import signal
import sys
import requests
import logging
import math
import os
import spawningtool.parser
from difflib import SequenceMatcher
from datetime import datetime, timedelta
from settings import config
from datetime import datetime
from collections import defaultdict

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


class GameInfo:
    def __init__(self, json_data):
        self.isReplay = json_data['isReplay']
        self.players = json_data['players']
        self.displayTime = json_data['displayTime']

    def get_player_names(self, result_filter=None):
        return [config.STREAMER_NICKNAME if player['name'] in config.SC2_PLAYER_ACCOUNTS else player['name'] for player
                in self.players if result_filter is None or player['result'] == result_filter]

    def get_status(self):
        if all(player['result'] == 'Undecided' for player in self.players):
            return "REPLAY_STARTED" if self.isReplay else "MATCH_STARTED"
        elif any(player['result'] in ['Defeat', 'Victory', 'Tie'] for player in self.players):
            return "REPLAY_ENDED" if self.isReplay else "MATCH_ENDED"
        return None

    def get_winner(self):
        for player in self.players:
            if player['result'] == 'Victory':
                return player['name']
        return None


class LogOnceWithinIntervalFilter(logging.Filter):
    """Logs each unique message only once within a specified time interval if they are similar."""

    def __init__(self, similarity_threshold=0.95, interval_seconds=120):
        super().__init__()
        self.similarity_threshold = similarity_threshold
        self.interval = timedelta(seconds=interval_seconds)
        self.last_logged_message = None
        self.last_logged_time = None

    def filter(self, record):
        now = datetime.now()

        time_left = None
        if self.last_logged_message:
            time_since_last_logged = now - self.last_logged_time
            time_left = self.interval - time_since_last_logged
            if time_since_last_logged < self.interval:
                similarity = SequenceMatcher(None, self.last_logged_message, record.msg).ratio()
                if similarity > self.similarity_threshold:
                    print(f"suppressed: {math.floor(time_left.total_seconds())} secs")
                    return False

        self.last_logged_message = record.msg
        self.last_logged_time = now
        return True


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

last_received_data = None
prev_results = None
first_run = True


def get_random_emote():
    emote_names = config.BOT_GREETING_EMOTES
    return f'{random.choice(emote_names)}'


# Global variable to save the path of the latest file found
latest_file_found = None


def find_latest_file(folder, file_extension):
    global latest_file_found

    try:
        if not os.path.isdir(folder):
            logger.debug(f"The provided path '{folder}' is not a directory. Please provide a valid directory path.")
            return None

        if not file_extension.startswith('.'):
            file_extension = '.' + file_extension

        logger.debug(f"Searching for files with extension '{file_extension}' in folder '{folder}' & subdirectories...")

        latest_file = None
        latest_timestamp = None

        for root, _, files in os.walk(folder):
            for filename in files:
                if filename.endswith(file_extension):
                    filepath = os.path.join(root, filename)
                    file_timestamp = os.path.getmtime(filepath)

                    if latest_file is None or file_timestamp > latest_timestamp:
                        latest_file = filepath
                        latest_timestamp = file_timestamp

        if latest_file:
            if latest_file == latest_file_found:
                logger.debug(f"The latest file with extension '{file_extension}' has not changed: {latest_file}")
            else:
                logger.debug(f"Found a new latest file with extension '{file_extension}': {latest_file}")
                latest_file_found = latest_file

            return latest_file
        else:
            logger.debug(
                f"No files with extension '{file_extension}' were found in the folder '{folder}' and its subdirectories.")
            return None

    except Exception as e:
        logger.debug(f"An error occurred while searching for the latest file: {e}")
        return None


class TwitchBot(irc.bot.SingleServerIRCBot):
    def __init__(self):

        # handle KeyboardInterrupt in a more graceful way by setting a flag when Ctrl-C is pressed and checking that
        # flag in threads that need to be terminated
        self.shutdown_flag = False
        signal.signal(signal.SIGINT, self.signal_handler)

        # threads to be terminated as soon as the main program finishes when set as daemon threads
        monitor_thread = threading.Thread(target=self.monitor_game)
        monitor_thread.daemon = True
        monitor_thread.start()

        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
        file_handler = logging.FileHandler('bot.log')
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
        self.selected_moods = [config.MOOD_OPTIONS[i] for i in config.BOT_MOODS]
        self.selected_perspectives = [config.PERSPECTIVE_OPTIONS[i] for i in config.BOT_PERSPECTIVES]

        # Initialize the IRC bot
        irc.bot.SingleServerIRCBot.__init__(self, [(self.server, self.port, 'oauth:' + self.token)], self.username,
                                            self.username)

    def signal_handler(self, frame):
        self.shutdown_flag = True
        logger.debug(
            "================================================SHUTTING DOWN BOT========================================")
        self.die("Shutdown requested.")
        sys.exit(0)

    @staticmethod
    def check_SC2_game_status():
        if config.TEST_MODE:
            try:
                with open('test/SC2_game_result_test.json', 'r') as file:
                    json_data = json.load(file)
                return GameInfo(json_data)
            except Exception as e:
                logger.debug(f"An error occurred while reading the test file: {e}")
                return None
        else:
            try:
                response = requests.get("http://localhost:6119/game")
                response.raise_for_status()
                return GameInfo(response.json())
            except Exception as e:
                logger.debug(f"An error occurred: {e}")
                return None

    def handle_SC2_game_results(self, previous_game, current_game):

        # do not proceed if no change
        if previous_game and current_game.get_status() == previous_game.get_status():
            return

        response = ""
        replay_summary = ""  # Initialize summary string

        logger.debug("game status is " + current_game.get_status())

        # prevent the array brackets from being included
        game_player_names = ', '.join(current_game.get_player_names())

        if current_game.get_status() in ("MATCH_ENDED", "REPLAY_ENDED"):
            result = find_latest_file(config.REPLAYS_FOLDER, config.REPLAYS_FILE_EXTENSION)
            if result:
                print(f"The path to the latest file is: {result}")
                #test
                #result="C:/Users/karl_/Downloads/twitch-gpt-chat-bot/test/replays/1v1 TESTFILE - no matching names - 20230805 - Game 2 - Solar vs Serral - ZvZ - Gresvan.sc2replay"
                replay_data = spawningtool.parser.parse_replay(result)

                # Save the replay JSON to a file
                filename = 'last_replay_data.json'
                with open(filename, 'w') as file:
                    json.dump(replay_data, file, indent=4)
                    logger.debug('last replay file saved: ' + filename)

                replay_data = spawningtool.parser.parse_replay(result)

                # Players and Map
                players = [f"{player_data['name']}: {player_data['race']}" for player_data in
                           replay_data['players'].values()]
                replay_summary += f"Players: {', '.join(players)}\n"
                print(replay_summary)

                replay_summary += f"Map: {replay_data['map']}\n\n"
                print(replay_summary[-len(f"Map: {replay_data['map']}\n\n"):])

                # Build Orders
                build_orders = {player_key: player_data['buildOrder'] for player_key, player_data in
                                replay_data['players'].items()}
                for player_key, build_order in build_orders.items():
                    player_info = f"{replay_data['players'][player_key]['name']}'s Build Order (first 20 steps):"
                    replay_summary += player_info + '\n'
                    print(player_info)
                    for order in build_order[:20]:
                        time = order['time']
                        name = order['name']
                        supply = order['supply']
                        order_info = f"Time: {time}, Name: {name}, Supply: {supply}"
                        replay_summary += order_info + '\n'
                        print(order_info)
                    replay_summary += '\n'
                    print()

                # Units Lost
                units_lost_summary = {player_key: player_data['unitsLost'] for player_key, player_data in
                                      replay_data['players'].items()}
                for player_key, units_lost in units_lost_summary.items():
                    player_info = f"{replay_data['players'][player_key]['name']}'s Units Lost:"
                    replay_summary += player_info + '\n'
                    print(player_info)
                    units_lost_aggregate = defaultdict(int)
                    for unit in units_lost:
                        name = unit.get('name', "N/A")
                        units_lost_aggregate[name] += 1
                    for unit_name, count in units_lost_aggregate.items():
                        unit_info = f"{unit_name}: {count}"
                        replay_summary += unit_info + '\n'
                        print(unit_info)
                    replay_summary += '\n'
                    print()

                # replace player names with streamer name
                for player_name in config.SC2_PLAYER_ACCOUNTS:
                    replay_summary = replay_summary.replace(player_name, config.STREAMER_NICKNAME)

                # Save the replay summary to a file
                filename = 'replay_summary.txt'
                with open(filename, 'w') as file:
                    file.write(replay_summary)
                    logger.debug('last replay summary saved: ' + filename)
                print("Replay data saved to replay_data.json")
            else:
                print("No result found or an error occurred.")

        if current_game.get_status() == "MATCH_STARTED":
            response = f"Game has started with these {game_player_names}"

        elif current_game.get_status() == "MATCH_ENDED":
            winning_players = ', '.join(current_game.get_player_names(result_filter='Victory'))
            losing_players = ', '.join(current_game.get_player_names(result_filter='Defeat'))

            if len(winning_players) == 0:
                response = f"Game with {game_player_names} ended with a Tie!"
            else:
                response = f"Game with {game_player_names} ended with {winning_players} beating {losing_players}"

        elif current_game.get_status() == "REPLAY_STARTED":
            response = f"{config.STREAMER_NICKNAME} is running a replay of the game with {game_player_names}"

        elif current_game.get_status() == "REPLAY_ENDED":
            winning_players = ', '.join(current_game.get_player_names(result_filter='Victory'))
            losing_players = ', '.join(current_game.get_player_names(result_filter='Defeat'))

            if len(winning_players) == 0:
                response = f"Replayed game with {game_player_names} ended with a Tie!"
            else:
                response = f"The replay has finished, game with {game_player_names} ended in a win for {winning_players} and a loss for {losing_players}"

        if not config.OPENAI_DISABLED:
            self.processMessageForOpenAI(response)
            # get analysis of game summary, from an SC2 viewer perspective
            self.processMessageForOpenAI(replay_summary)

    def monitor_game(self):
        previous_game = None

        while True and not self.shutdown_flag:
            current_game = self.check_SC2_game_status()

            if current_game:
                if not config.IGNORE_REPLAYS or not current_game.isReplay:
                    self.handle_SC2_game_results(previous_game, current_game)

            previous_game = current_game
            time.sleep(config.MONITOR_GAME_SLEEP_SECONDS)

    # all msgs to channel are now logged
    def msgToChannel(self, message):
        self.connection.privmsg(self.channel, message)
        logger.debug("---------------------MSG TO CHANNEL----------------------")
        logger.debug(message)
        logger.debug("---------------------------------------------------------")

    def processMessageForOpenAI(self, msg):
        # remove open sesame
        msg = msg.replace('open sesame', '')
        logger.debug(
            "----------------------------------------NEW MESSAGE FOR OPENAI-----------------------------------------")
        logger.debug(msg)
        # remove open sesame
        msg = msg.replace('open sesame', '')

        # remove quotes
        msg = msg.replace('"', '')
        msg = msg.replace("'", '')

        # add line break to ensure separation
        msg = msg + "\n"

        # TODO: redo this logic
        # if bool(config.STOP_WORDS_FLAG):
        #    msg, removedWords = tokensArray.apply_stop_words_filter(msg)
        #    logger.debug("removed stop words: %s" , removedWords)

        # add User msg to conversation context
        tokensArray.add_new_msg(contextHistory, 'User: ' + msg + "\n", logger)

        # add complete array as msg to OpenAI
        msg = msg + tokensArray.get_printed_array("reversed", contextHistory)

        # Choose a random mood and perspective from the selected options
        mood = random.choice(self.selected_moods)
        perspective = random.choice(self.selected_perspectives)

        # Add custom SC2 viewer perspective
        msg = (f"As a {mood} observer of matches in StarCraft 2, {perspective}, "
               f"without repeating any previous words from here: /n") + msg + "\n"
        msg += (" Do not use personal pronouns like 'I,' 'me,' 'my,' etc. "
                "but instead speak from a 3rd person referencing the player.")

        logger.debug("sent to OpenAI: %s", msg)
        completion = openai.ChatCompletion.create(
            model=config.ENGINE,
            messages=[
                {"role": "user", "content": msg}
            ]
        )
        if completion.choices[0].message is not None:
            logger.debug("completion.choices[0].message.content: " + completion.choices[0].message.content)
            response = completion.choices[0].message.content

            # add emote
            if random.choice([True, False]):
                response = f'{response} {get_random_emote()}'

            logger.debug('raw response from OpenAI:')
            logger.debug(response)

            # Clean up response
            response = re.sub('[\r\n\t]', ' ', response)  # Remove carriage returns, newlines, and tabs
            response = re.sub('[^\x00-\x7F]+', '', response)  # Remove non-ASCII characters
            response = re.sub(' +', ' ', response)  # Remove extra spaces
            response = response.strip()  # Remove leading and trailing whitespace

            # dont make it too obvious its a bot
            response = response.replace("As an AI language model, ", "")
            response = response.replace("User: , ", "")

            logger.debug("cleaned up message from OpenAI:")
            logger.debug(response)

            if len(response) >= 400:
                logger.debug(f"Chunking response since it's {len(response)} characters long")

                # Split the response into chunks of 400 characters without splitting words
                chunks = []
                temp_chunk = ''
                for word in response.split():
                    if len(temp_chunk + ' ' + word) <= 400:
                        temp_chunk += ' ' + word if temp_chunk != '' else word
                    else:
                        chunks.append(temp_chunk)
                        temp_chunk = word
                if temp_chunk:
                    chunks.append(temp_chunk)

                # Send response chunks to chat
                for chunk in chunks:
                    # Remove all occurrences of "AI: "
                    chunk = re.sub(r'\bAI: ', '', chunk)
                    self.msgToChannel(chunk)

                    # Add AI response to conversation context
                    tokensArray.add_new_msg(contextHistory, 'AI: ' + chunk + "\n", logger)

                    # Log relevant details
                    logger.debug(f'Sending openAI response chunk: {chunk}')
                    logger.debug(
                        f'Conversation in context so far: {tokensArray.get_printed_array("reversed", contextHistory)}')
            else:
                response = re.sub(r'\bAI: ', '', response)
                self.msgToChannel(response)

                # Add AI response to conversation context
                tokensArray.add_new_msg(contextHistory, 'AI: ' + response + "\n", logger)

                # Log relevant details
                logger.debug(f'AI msg to chat: {response}')
                logger.debug(
                    f'Conversation in context so far: {tokensArray.get_printed_array("reversed", contextHistory)}')

        else:
            response = 'oops, I have no response to that'
            self.msgToChannel(response)
            logger.debug('Failed to send response: %s', response)

    def on_welcome(self, connection, event):
        # Join the channel and say a greeting
        connection.join(self.channel)
        logger.debug(
            "================================================STARTING BOT========================================")
        prefix = ""  # if any
        greeting_message = f'{prefix} {get_random_emote()}'
        self.msgToChannel(greeting_message)

    def on_pubmsg(self, connection, event):

        # Get message from chat
        msg = event.arguments[0].lower()
        sender = event.source.split('!')[0]
        # tags = {kvpair["key"]: kvpair["value"] for kvpair in event.tags}
        # user = {"name": tags["display-name"], "id": tags["user-id"]}

        # Send response to direct msg or keyword which includes Mathison being mentioned
        if 'open sesame' in msg.lower() or any(sub in msg.lower() for sub in config.OPEN_SESAME_SUBSTITUTES):
            self.processMessageForOpenAI(msg)
            return

        # ignore certain users
        if sender.lower() in [user.lower() for user in config.IGNORE]:
            logger.debug("ignoring user: " + sender)
            return

        if config.PERSPECTIVE_DISABLED:
            toxicity_probability = 0
        else:
            toxicity_probability = tokensArray.get_toxicity_probability(msg, logger)
        # do not send toxic messages to openAI
        if toxicity_probability < config.TOXICITY_THRESHOLD:

            # any user greets via config keywords will be responded to
            if any(greeting in msg.lower() for greeting in config.GREETINGS_LIST_FROM_OTHERS):
                response = f"Hi {sender}!"
                response = f'{response} {get_random_emote()}'
                self.msgToChannel(response)
                # disable the return - sometimes it matches words so we want mathison to reply anyway
                # DO NOT return

            if 'bye' in msg.lower():
                response = f"bye {sender}!"
                self.msgToChannel(response)
                return

            if 'gg' in msg.lower():
                response = f"HSWP"
                self.msgToChannel(response)
                return

            if 'bracket' in msg.lower() or '!b' in msg.lower() or 'FSL' in msg.upper() or 'fsl' in msg.lower():
                response = f"here is some info {config.BRACKET}"
                self.msgToChannel(response)
                return

            # will only respond to a certain percentage of messages per config
            diceRoll = random.randint(0, 100) / 100
            logger.debug("rolled: " + str(diceRoll) + " settings: " + str(config.RESPONSE_PROBABILITY))
            if diceRoll >= config.RESPONSE_PROBABILITY:
                logger.debug("will not respond")
                return

            self.processMessageForOpenAI(msg)

        else:
            response = random.randint(1, 3)
            switcher = {
                1: f"{sender}, please refrain from sending toxic messages.",
                2: f"Woah {sender}! Strong language",
                3: f"Calm down {sender}. What's with the attitude?"
            }
            self.msgToChannel(switcher.get(response))


username = config.USERNAME
token = config.TOKEN  # get this from https://twitchapps.com/tmi/
channel = config.USERNAME


async def tasks_to_do():
    try:
        # Create an instance of the bot and start it
        bot = TwitchBot()
        await bot.start()
    except SystemExit as e:
        # Handle the SystemExit exception if needed, or pass to suppress it
        pass


async def main():
    tasks = [asyncio.create_task(tasks_to_do())]
    for task in tasks:
        await task  # Await the task here to handle exceptions


asyncio.run(main())
