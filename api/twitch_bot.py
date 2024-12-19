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
import api.text2speech as ts
import speech_recognition as sr
import api.chat_utils as chat_utils
import tempfile  # For creating temporary files
import sounddevice as sd  # For audio recording
import scipy.io.wavfile as wavfile  # For saving audio as WAV
import os  # For file operations (e.g., removing temporary files)
import numpy as np  # For numerical operations

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
from .game_event_utils import game_started_handler
from .game_event_utils import game_replay_handler
from .game_event_utils import game_ended_handler
from .chat_utils import message_on_welcome, process_pubmsg
from .sc2_game_utils import handle_SC2_game_results

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

        # Start the speech listener thread
        if config.USE_WHISPER is True:
            speech_thread = threading.Thread(target=self.listen_for_speech_whisperAI)
        else:
            speech_thread = threading.Thread(target=self.listen_for_speech)
        speech_thread.daemon = True
        speech_thread.start()        

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
            self.sound_player.play_sound(game_event, logger)
        else:
            logger.debug("SC2 player intros and other sounds are disabled")

    # incorrect IDE warning here, keep parameters at 3
    def signal_handler(self, signal, frame):
        self.shutdown_flag = True
        logger.debug(
            "================================================SHUTTING DOWN BOT========================================")
        self.die("Shutdown requested.")
        sys.exit(0)

    def listen_for_speech_whisperAI(self):
        def is_audio_silent(audio_data, threshold=0.01):
            """Check if the audio data is silent based on RMS value."""
            rms = np.sqrt(np.mean(audio_data**2))
            return rms < threshold

        def filter_to_english(text):
            """Filter transcription to only include ASCII/English characters."""
            return ''.join(c for c in text if ord(c) < 128)

        msg = str("")
        buffer = ""  # To aggregate results from smaller chunks

        while not self.shutdown_flag:
            try:
                chunk_duration = 3  # Initial recording duration in seconds
                fs = 16000  # Sample rate

                while True:
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                        temp_filename = tmp_file.name

                    print("o", end="", flush=True)
                    audio_data = sd.rec(int(chunk_duration * fs), samplerate=fs, channels=1, dtype='int16')
                    sd.wait()  # Wait until recording is finished

                    # Check if speech starts within the recorded chunk
                    if not is_audio_silent(audio_data):
                        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as extended_tmp_file:
                            extended_filename = extended_tmp_file.name
                            extended_audio_data = sd.rec(int(chunk_duration * fs), samplerate=fs, channels=1, dtype='int16')
                            sd.wait()
                            extended_audio_data = np.concatenate((audio_data, extended_audio_data), axis=0)

                            # Write the concatenated audio to a file
                            wavfile.write(extended_filename, fs, extended_audio_data)

                        # Use Whisper API for transcription
                        with open(extended_filename, "rb") as audio_file:
                            response = openai.Audio.transcribe("whisper-1", audio_file)
                            partial_command = response.get("text", "").strip().lower()

                        os.remove(extended_filename)  # Clean up temporary file

                        # Filter transcription to only ASCII/English characters
                        partial_command = filter_to_english(partial_command)

                        # Skip empty or meaningless transcriptions
                        if not partial_command or partial_command in {".", ". ."}:
                            os.remove(temp_filename)  # Clean up temporary file
                            continue

                        # Append to buffer and handle natural pauses
                        buffer += f" {partial_command}".strip()

                        # Check if the buffer contains complete sentences
                        if buffer.endswith(('.', '!', '?')):
                            command = buffer.strip()
                            buffer = ""  # Clear the buffer for the next input
                            if command not in {".", ". ."}:
                                logger.debug(f"Full transcription: '{command}'")

                            # Process the full command
                            for keywords, responses in config.SPEECH2TEXT_OPTIONS:
                                if any(word in command for word in keywords):
                                    logger.debug(f"Command recognized: '{keywords[0]}' or similar")
                                    msg = str(responses[0]) if isinstance(responses, list) and len(responses) > 0 else str(responses)
                                    self.play_SC2_sound(keywords[0])
                                    chat_utils.processMessageForOpenAI(self, msg, "helpful", logger, contextHistory)
                                    break

                            if "adios" in command:
                                logger.debug("Exit command recognized. Stopping the bot.")
                                self.shutdown_flag = True
                                break
                            elif "hey madison" in command:
                                ts.speak_text("yes?")
                                # Handle follow-up commands here if needed
                        os.remove(temp_filename)  # Clean up temporary file
                    else:
                        os.remove(temp_filename)  # Clean up temporary file
                        continue
            except Exception as e:
                logger.error(f"Error during speech recognition: {e}")
                time.sleep(2)

    def listen_for_speech(self):
        recognizer = sr.Recognizer()
        mic = sr.Microphone()
        msg = str("")

        with mic as source:
            recognizer.adjust_for_ambient_noise(source)
            while not self.shutdown_flag:
                try:
                    # Listen for the cue word "hey madison"
                    #logger.debug("Listening for 'hey madison' cue...")
                    print("o", end="", flush=True)
                    audio = recognizer.listen(source, phrase_time_limit=2)  # Limit listening to 2 seconds

                    command = recognizer.recognize_google(audio).lower()
                    logger.debug(f"'{command}'")

                    # Iterate through the SPEECH2TEXT_OPTIONS in config
                    for keywords, responses in config.SPEECH2TEXT_OPTIONS:
                        # logger.debug(f"Inspecting keywords: {keywords}, responses: {responses}")
                        if any(word in command for word in keywords):
                            logger.debug(f"Command recognized: '{keywords[0]}' or similar")

                            # Ensure that the response is captured correctly as a full string
                            msg = str(responses[0]) if isinstance(responses, list) and len(responses) > 0 else str(responses)

                            # Log the keyword and message to debug
                            # logger.debug(f"keyword and msg are: {keywords[0]}, {msg}")

                            self.play_SC2_sound(keywords[0])  # Use the first keyword as the sound identifier
                            chat_utils.processMessageForOpenAI(self, msg, "helpful", logger, contextHistory)

                            break

                    if "adios" in command:
                        logger.debug("Exit command recognized. Stopping the bot.")
                        self.shutdown_flag = True
                        break
                    elif "hey madison" in command:
                        #logger.debug("Cue recognized: 'hey madison'. Waiting for command...")
                        ts.speak_text("yes?")
                        
                        # Listen for the follow-up command
                        try:
                            audio = recognizer.listen(source, phrase_time_limit=2)
                            follow_up_command = recognizer.recognize_google(audio).lower()
                            logger.debug(f"Follow-up command: '{follow_up_command}'")

                            if "smile" in follow_up_command:
                                logger.debug("Command recognized: 'smile'")
                                # Add your handling code here
                                ts.speak_text("I'm smiling!")
                            else:
                                logger.debug(f"Unhandled follow-up command: '{follow_up_command}'")
                                ts.speak_text("I didn't understand that.")

                        except sr.UnknownValueError:
                            logger.debug("Could not understand the follow-up command.")
                            ts.speak_text("I didn't catch that.")
                        except sr.RequestError as e:
                            logger.error(f"Request error from speech recognition service: {e}")
                            time.sleep(2)
                        except Exception as e:
                            #logger.error(f"Error during speech recognition: {e}")
                            print("e", end="", flush=True)
                            time.sleep(2)
                    
                    else:
                        print("?", end="", flush=True)
                        
                except sr.UnknownValueError:
                    print("x", end="", flush=True)
                except sr.RequestError as e:
                    logger.error(f"Request error from speech recognition service: {e}")
                    time.sleep(2)  # Prevent rapid retries
                except Exception as e:
                    #logger.error(f"Error during speech recognition: {e}")
                    print("e", end="", flush=True)
                    time.sleep(2)  # Prevent rapid retries

    def monitor_game(self):
        previous_game = None
        heartbeat_counter = 0
        heartbeat_interval = config.HEARTBEAT_MYSQL  # Number of iterations before sending a heartbeat for MySQL

        while not self.shutdown_flag:
            try:
                current_game = check_SC2_game_status(logger)
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
                        # self.handle_SC2_game_results(
                        #    previous_game, current_game)
                        handle_SC2_game_results(self, previous_game,
                                                 current_game, contextHistory, logger)

                previous_game = current_game
                time.sleep(config.MONITOR_GAME_SLEEP_SECONDS)

                # Increment the heartbeat counter
                heartbeat_counter += 1

                # Check if it's time to send a heartbeat
                if heartbeat_counter >= heartbeat_interval:
                    try:
                        self.db.keep_connection_alive()
                        heartbeat_counter = 0  # Reset the counter after sending the heartbeat
                        # heartbeat indicator
                        print("+", end="", flush=True)                        
                    except Exception as e:
                        self.logger.error(f"Error during database heartbeat call: {e}")                       
                else:
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