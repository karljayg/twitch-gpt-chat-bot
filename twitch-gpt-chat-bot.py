import irc.bot
import requests
import logging
import openai
import re
from settings import config
import tokensArray
import asyncio
import random

# The contextHistory array is a list of tuples, where each tuple contains two elements: the message string and its corresponding token size. This allows us to keep track of both the message content and its size in the array.
# When a new message is added to the contextHistory array, its token size is determined using the nltk.word_tokenize() function. If the total number of tokens in the array exceeds the maxContextTokens threshold, the function starts deleting items from the end of the array until the total number of tokens is below the threshold.
# If the last item in the array has a token size less than or equal to the maxContextTokens threshold, the item is removed completely. However, if the last item has a token size greater than the threshold, the function removes tokens from the end of the message string until its token size is less than or equal to the threshold, and keeps the shortened message string in the array.
# If the total number of tokens in the array is still above the threshold after deleting the last item, the function repeats the process with the second-to-last item in the array, and continues deleting items until the total number of tokens is below the threshold.
# By using this logic, we can ensure that the contextHistory array always contains a maximum number of tokens specified by maxContextTokens, while keeping the most recent messages in the array.
global contextHistory
contextHistory = []

import json
import random
import requests
import time
import pygame
from enum import Enum
import logging
import urllib3
import sys
import threading
import signal
import sys
import requests
from requests.exceptions import JSONDecodeError
from difflib import SequenceMatcher
from datetime import datetime, timedelta
import logging
import math

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
                #print("similarity criteria: " + str(math.floor(similarity)) + "/" + str(self.similarity_threshold), end = " ")
                if similarity > self.similarity_threshold:
                    #print(f"suppressed: {math.floor(time_left.total_seconds())} secs left from original {self.interval.total_seconds()} sec")
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


# This monitors SC2 game state so bot can comment on it
class GameState(Enum):
    STARTED = 'Undecided'
    ENDED = ['Defeat', 'Victory', 'Tie']

# Player names of streamer to check results for
player_names = config.SC2_PLAYER_ACCOUNTS

last_received_data = None
prev_results = None
first_run = True

def get_game_status():
    global prev_results, first_run

    try:
        response = requests.get('http://localhost:6119/game')
        data = response.json()
        current_results = {player['id']: {'name': player['name'], 'result': player['result']} for player in data['players']}

        if first_run:
            print ("first run, not checking previous game results")
            prev_results = current_results
            first_run = False
            return None, None, None

        if current_results == prev_results: # Check if the results are the same as last time
            return None, None, None # Return None if there's no change
    
        prev_results = current_results # Update previous results
    
        # Extract the player names and results
        player_names = [info['name'] for info in current_results.values()]
        player_results = [info['result'] for info in current_results.values()]

        # Determine the game status. You can adapt this based on your game logic
        game_status = 'STARTED' if 'Undecided' in player_results else 'ENDED'

        print(f"Received data: {data}")  # Print the JSON data only if there's a change in results
        print(f"Player names and results: {current_results}")
        print(f"Game status: {game_status}")

        return player_names, game_status, player_results
    except JSONDecodeError:
        logger.debug("StarCraft game is not running")
        return None, None, None
    except Exception as e:
        logger.debug(f"An unexpected error occurred: {e}")
        return None, None, None

class TwitchBot(irc.bot.SingleServerIRCBot):
    def __init__(self, username, token, channel):

        #handle KeyboardInterrupt in a more graceful way by setting a flag when Ctrl-C is pressed and checking that flag in threads
        self.shutdown_flag = False
        signal.signal(signal.SIGINT, self.signal_handler)

        #threads to be terminated as soon as the main program finishes when set as daemon threads
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

        # Initialize the IRC bot
        irc.bot.SingleServerIRCBot.__init__(self, [(self.server, self.port, 'oauth:'+self.token)], self.username, self.username)

    def signal_handler(self, signal, frame):
        self.shutdown_flag = True
        self.die("Shutdown requested.")
        sys.exit(0)

    def handle_game_result(self, player_names, game_status, player_results):
        player_name_0 = player_names[0] if player_names[0] not in config.SC2_PLAYER_ACCOUNTS else config.STREAMER_NICKNAME
        player_name_1 = player_names[1] if player_names[1] not in config.SC2_PLAYER_ACCOUNTS else config.STREAMER_NICKNAME
        response = ""
        if game_status == 'STARTED':
            response = f"Game has started between {player_name_0} and {player_name_1}"
        elif game_status == 'ENDED':
            response = f"Game has ended between {player_name_0} ({player_results[0].lower()}) and {player_name_1} ({player_results[1].lower()})"
        self.processMessageForOpenAI(response)

    def monitor_game(self):
        previous_game_status = 'STARTED'  # Initialize with STARTED
        while True and not self.shutdown_flag:
            player_names, game_status, player_results = get_game_status()
            if player_names is None and game_status is None:
                time.sleep(config.MONITOR_GAME_SLEEP_SECONDS)  # Wait a second if there's no change
                continue # Skip the rest of the loop if there's no change

            if game_status != previous_game_status:
                # Handle game result
                self.handle_game_result(player_names, game_status, player_results)
                previous_game_status = game_status
            time.sleep(config.MONITOR_GAME_SLEEP_SECONDS)  # Wait a second before re-checking

    def get_random_emote(self):
        emote_names = config.BOT_GREETING_EMOTES
        return f'{random.choice(emote_names)}'        

    #all msgs to channel are now logged
    def msgToChannel(self, message):
        self.connection.privmsg(self.channel, message)
        logger.debug("msg to channel: " + message)

    def processMessageForOpenAI(self, msg):
        #remove open sesame
        msg = msg.replace('open sesame', '')

        #remove quotes
        msg = msg.replace('"', '')
        msg = msg.replace("'", '')

        # TODO: redo this logic
        #if bool(config.STOP_WORDS_FLAG):
        #    msg, removedWords = tokensArray.apply_stop_words_filter(msg)
        #    logger.debug("removed stop words: %s" , removedWords)

        #add User msg to conversation context
        tokensArray.add_new_msg(contextHistory, 'User: ' + msg + "\n", logger)

        #add complete array as msg to OpenAI
        msg = msg + tokensArray.get_printed_array("reversed", contextHistory)

        #add custom SC2 viewer perspective
        msg = "As a subtly funny observer of matches in StarCraft 2, respond casually and concisely in only 20 words, without repeating any previous words from here: " + msg
        msg += " Do not use personal pronouns like 'I,' 'me,' 'my,' etc. but instead speak from a 3rd person referencing the player."


        logger.debug("sent to OpenAI: %s" , msg)
        completion = openai.ChatCompletion.create(
            model=config.ENGINE,
            messages=[
                {"role": "user", "content": msg}
            ]
        )
        if completion.choices[0].message!=None:
            print(completion.choices[0].message.content)
            response = completion.choices[0].message.content

            #dont make it too obvious its a bot
            response = response.replace("As an AI language model, ", "")

            #add emote
            response = f'{response} {self.get_random_emote()}'

            # Clean up response
            print('raw response from OpenAI: %s', response)
            response = re.sub('[\r\n\t]', ' ', response)  # Remove carriage returns, newlines, and tabs
            response = re.sub('[^\x00-\x7F]+', '', response)  # Remove non-ASCII characters
            response = re.sub(' +', ' ', response) # Remove extra spaces
            response = response.strip() # Remove leading and trailing whitespace

            # Split the response into chunks of 400 characters, without splitting the words
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
                #remove all occurences of "AI: "
                chunk = re.sub(r'\bAI: ', '', chunk)
                self.msgToChannel(chunk)
                logger.debug('Sending openAI response chunk: %s', chunk)

                #add AI response to conversation context
                print("AI msg to chat: " + chunk)
                tokensArray.add_new_msg(contextHistory, 'AI: ' + chunk + "\n", logger)
                #print conversation so far
                print(tokensArray.get_printed_array("reversed", contextHistory))
        else:
            response = 'Failed to generate response!'
            self.msgToChannel(response)
            logger.debug('Failed to send response: %s', response)

    def on_welcome(self, connection, event):
        # Join the channel and say a greeting
        connection.join(self.channel)
        prefix="" #if any
        greeting_message = f'{prefix} {self.get_random_emote()}'
        self.msgToChannel(greeting_message)
        threading.Thread(target=self.monitor_game).start()  # Start a thread to monitor the game

    def on_pubmsg(self, connection, event):

        # Get message from chat
        msg = event.arguments[0].lower()
        sender = event.source.split('!')[0]
        #tags = {kvpair["key"]: kvpair["value"] for kvpair in event.tags}
        #user = {"name": tags["display-name"], "id": tags["user-id"]}

        #ignore certain users
        if sender.lower() in [user.lower() for user in config.IGNORE]:
            logger.debug("ignoring user: " + sender)
            return

        if config.PERSPECTIVE_DISABLED:
            toxicity_probability = 0
        else:
            toxicity_probability = tokensArray.get_toxicity_probability(msg, logger)
        #do not send toxic messages to openAI
        if toxicity_probability < config.TOXICITY_THRESHOLD:                                 

            # any user greets via config keywords will be responded to
            if any(greeting in msg.lower() for greeting in config.GREETINGS_LIST_FROM_OTHERS):
                response = f"Hi {sender}!"
                response = f'{response} {self.get_random_emote()}'
                self.msgToChannel(response)
                #disable the return - sometimes it matches words so we want mathison to reply anyway
                #return

            # will only respond to a certain percentage of messages per config
            diceRoll=random.randint(0,100)/100
            logger.debug("rolled: " + str(diceRoll) + " settings: " + str(config.RESPONSE_PROBABILITY))        
            if diceRoll >= config.RESPONSE_PROBABILITY:
                logger.debug("will not respond")        
                return

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

            # Send response to direct msg or keyword which includes Mathison being mentioned
            if 'open sesame' in msg.lower() or any(sub in msg.lower() for sub in config.OPEN_SESAME_SUBSTITUTES):   
                self.processMessageForOpenAI(msg)
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
token = config.TOKEN # get this from https://twitchapps.com/tmi/
channel = config.USERNAME

async def tasks_to_do():
    # Create an instance of the bot and start it
    bot = TwitchBot(username, token, channel)
    await bot.start()

async def main():
    tasks = []
    tasks.append(asyncio.create_task(tasks_to_do()))
    await asyncio.gather(tasks)

asyncio.run(main())
