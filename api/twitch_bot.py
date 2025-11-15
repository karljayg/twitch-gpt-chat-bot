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
import api.chat_utils as chat_utils
import tempfile  # For creating temporary files
import os  # For file operations (e.g., removing temporary files)
import re

from datetime import datetime
from collections import defaultdict

from settings import config

# Force shutdown handler to prevent hanging on Ctrl+C
def force_shutdown(sig, frame):
    print('\nReceived interrupt signal - forcing immediate exit...')
    sys.exit(0)

# Register the signal handler
signal.signal(signal.SIGINT, force_shutdown)

# Initialize basic logger for import warnings
import logging
_import_logger = logging.getLogger(__name__)

# Conditional audio imports - only import when audio features are enabled
# This allows the bot to run on servers without audio libraries installed
if getattr(config, 'ENABLE_AUDIO', True):
    try:
        import api.text2speech as ts
        AUDIO_IMPORTS_AVAILABLE = True
    except ImportError as e:
        _import_logger.warning(f"Text-to-speech imports failed: {e}. TTS will be disabled.")
        AUDIO_IMPORTS_AVAILABLE = False
        ts = None
        
    if getattr(config, 'ENABLE_SPEECH_TO_TEXT', True):
        try:
            import speech_recognition as sr
            import sounddevice as sd  # For audio recording
            import scipy.io.wavfile as wavfile  # For saving audio as WAV
            import numpy as np  # For numerical operations
            STT_IMPORTS_AVAILABLE = True
        except ImportError as e:
            _import_logger.warning(f"Speech-to-text imports failed: {e}. STT will be disabled.")
            STT_IMPORTS_AVAILABLE = False
            sr = None
            sd = None
            wavfile = None
            np = None
    else:
        STT_IMPORTS_AVAILABLE = False
        sr = None
        sd = None 
        wavfile = None
        np = None
else:
    AUDIO_IMPORTS_AVAILABLE = False
    STT_IMPORTS_AVAILABLE = False
    ts = None
    sr = None
    sd = None
    wavfile = None
    np = None
import utils.tokensArray as tokensArray
import utils.wiki_utils as wiki_utils
from models.mathison_db import Database
from models.log_once_within_interval_filter import LogOnceWithinIntervalFilter
from utils.emote_utils import get_random_emote
from utils.file_utils import find_latest_file
# Conditional game sound imports
if getattr(config, 'ENABLE_AUDIO', True) and getattr(config, 'ENABLE_GAME_SOUNDS', True):
    try:
        from utils.sound_player_utils import SoundPlayer
        GAME_SOUNDS_AVAILABLE = True
    except ImportError as e:
        _import_logger.warning(f"Game sound imports failed: {e}. Game sounds will be disabled.")
        GAME_SOUNDS_AVAILABLE = False
        SoundPlayer = None
else:
    GAME_SOUNDS_AVAILABLE = False
    SoundPlayer = None
from api.sc2_game_utils import check_SC2_game_status
from api.game_event_utils import game_started_handler
from api.game_event_utils import game_replay_handler
from api.game_event_utils import game_ended_handler
from api.chat_utils import message_on_welcome, process_pubmsg
from api.sc2_game_utils import handle_SC2_game_results
# Ensure database initialization
from models.mathison_db import Database

# Pattern learning imports
try:
    from api.pattern_learning import SC2PatternLearner
    PATTERN_LEARNING_AVAILABLE = True
except ImportError as e:
    _import_logger.warning(f"Pattern learning imports failed: {e}. Pattern learning will be disabled.")
    PATTERN_LEARNING_AVAILABLE = False
    SC2PatternLearner = None

# FSL integration imports 
try:
    from api.fsl_integration import FSLIntegration
    FSL_IMPORTS_AVAILABLE = True
except ImportError as e:
    _import_logger.warning(f"FSL integration imports failed: {e}. FSL integration will be disabled.")
    FSL_IMPORTS_AVAILABLE = False
    FSLIntegration = None

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

# Suppress Discord gateway debug messages (websocket heartbeats)
logging.getLogger('discord.gateway').setLevel(logging.INFO)

# Simple indicator tracking without messing with logging system

# Track indicator sequences
_indicator_counts = {}  # Track counts of each indicator type  
_last_log_time = None  # Track when the last log message occurred

def _print_indicator_summary():
    """Print summary of indicators when interrupted by log output."""
    global _indicator_counts, _last_log_time
    import time  # Import at function start to avoid scoping issues
    
    # Indicator descriptions
    indicator_names = {
        '.': 'normal',
        'o': 'errors', 
        '+': 'events',
        'x': 'unknown',
        '?': 'waiting',
        'e': 'exceptions'
    }
    
    try:
        if _indicator_counts and _last_log_time:
            # Calculate elapsed time since last log message
            elapsed_seconds = time.time() - _last_log_time
            hours = int(elapsed_seconds // 3600)
            minutes = int((elapsed_seconds % 3600) // 60)
            seconds = int(elapsed_seconds % 60)
            elapsed_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            # Build summary string with counts and elapsed time
            total_indicators = sum(_indicator_counts.values())
            if total_indicators >= 1:
                count_parts = [f"{count} {indicator_names.get(indicator, indicator)}" for indicator, count in _indicator_counts.items()]
                count_str = " and ".join(count_parts)
                print(f" [elapsed: {elapsed_str}, {count_str} total]", flush=True)
        elif _indicator_counts:
            # No last log time tracked, just show counts
            total_indicators = sum(_indicator_counts.values())
            if total_indicators >= 1:
                count_parts = [f"{count} {indicator_names.get(indicator, indicator)}" for indicator, count in _indicator_counts.items()]
                count_str = " and ".join(count_parts)
                print(f" [{count_str} total]", flush=True)
    except Exception:
        pass  # Silently ignore any errors in summary
    
    # Update last log time and reset tracking
    _last_log_time = time.time()
    _indicator_counts = {}

def print_indicator(indicator):
    """
    Print single-character status indicator with smart spacing.
    
    Visual indicators provide real-time system status without verbose logging:
    - '.' = Normal operation (SC2 API working, heartbeat, etc.)
    - 'o' = Errors or issues (SC2 API failures, speech recognition issues)
    - '+' = Special events (database heartbeat, successful operations)
    - 'x' = Speech recognition unknown value
    - '?' = Speech recognition waiting/unclear state
    - 'e' = Exception occurred
    
    Smart spacing: If the previous output was a log message, this adds a newline
    before the indicator to visually separate it from the log text. Otherwise,
    indicators are printed consecutively on the same line.
    
    Args:
        indicator (str): Single character to print as status indicator
    """
    global _indicator_counts
    
    # Just track indicator counts - timing handled in summary function
    
    # Count this indicator
    _indicator_counts[indicator] = _indicator_counts.get(indicator, 0) + 1
    
    # Print the indicator
    print(indicator, end="", flush=True)

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
        
        # Pending player comment state for overwrite confirmation
        self.pending_player_comment = None  # Stores: {'comment': str, 'replay': dict, 'timestamp': int}

        # handle KeyboardInterrupt in a more graceful way by setting a flag when Ctrl-C is pressed and checking that
        # flag in threads that need to be terminated
        self.shutdown_flag = False
        signal.signal(signal.SIGINT, self.signal_handler)

        # threads to be terminated as soon as the main program finishes when set as daemon threads
        monitor_thread = threading.Thread(target=self.monitor_game)
        monitor_thread.daemon = True
        monitor_thread.start()

        # Start the speech listener thread only if speech-to-text is enabled and imports are available
        if (getattr(config, 'ENABLE_AUDIO', True) and 
            getattr(config, 'ENABLE_SPEECH_TO_TEXT', True) and 
            STT_IMPORTS_AVAILABLE):
            _import_logger.info("Starting speech recognition thread...")
            if getattr(config, 'USE_WHISPER', False) is True:
                speech_thread = threading.Thread(target=self.listen_for_speech_whisperAI)
            else:
                speech_thread = threading.Thread(target=self.listen_for_speech)
            speech_thread.daemon = True
            speech_thread.start()
        else:
            _import_logger.info("Speech recognition disabled - skipping speech thread startup")        

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
        # OpenAI API key is now set per-request in send_prompt_to_openai
        # openai.api_key = config.OPENAI_API_KEY

        self.streamer_nickname = config.STREAMER_NICKNAME
        self.selected_moods = [config.MOOD_OPTIONS[i]
                               for i in config.BOT_MOODS]
        self.selected_perspectives = [
            config.PERSPECTIVE_OPTIONS[i] for i in config.BOT_PERSPECTIVES]

        # Initialize the IRC bot
        irc.bot.SingleServerIRCBot.__init__(self, [(self.server, self.port, 'oauth:' + self.token)], self.username,
                                            self.username)
        
        # Initialize SC2 sounds only if available and enabled
        if GAME_SOUNDS_AVAILABLE and SoundPlayer is not None:
            try:
                self.sound_player = SoundPlayer()
                _import_logger.info("Game sounds initialized successfully")
            except Exception as e:
                _import_logger.error(f"Failed to initialize game sounds: {e}")
                self.sound_player = None
        else:
            self.sound_player = None
            _import_logger.info("Game sounds disabled - no SoundPlayer initialized")

        # Initialize the database
        self.db = Database()
        
        # Initialize FSL integration if available and enabled
        if (getattr(config, 'ENABLE_FSL_INTEGRATION', False) and 
            FSL_IMPORTS_AVAILABLE and FSLIntegration is not None):
            try:
                self.fsl_integration = FSLIntegration(
                    api_url=config.FSL_API_URL,
                    api_token=config.FSL_API_TOKEN,
                    reviewer_weight=config.FSL_REVIEWER_WEIGHT
                )
                _import_logger.info("FSL integration initialized successfully")
            except Exception as e:
                _import_logger.error(f"Failed to initialize FSL integration: {e}")
                self.fsl_integration = None
        else:
            self.fsl_integration = None
            _import_logger.info("FSL integration disabled - no FSLIntegration initialized")

        # Initialize pattern learning system if available and enabled
        if (getattr(config, 'ENABLE_PATTERN_LEARNING', False) and 
            PATTERN_LEARNING_AVAILABLE and SC2PatternLearner is not None):
            try:
                self.pattern_learner = SC2PatternLearner(self.db, logger)
                _import_logger.info("Pattern learning system initialized successfully")
            except Exception as e:
                _import_logger.error(f"Failed to initialize pattern learning: {e}")
                self.pattern_learner = None
        else:
            self.pattern_learner = None
            _import_logger.info("Pattern learning disabled - no SC2PatternLearner initialized")

    def play_SC2_sound(self, game_event):
        # Check if game sounds are available and enabled
        if not (getattr(config, 'ENABLE_AUDIO', True) and 
                getattr(config, 'ENABLE_GAME_SOUNDS', True) and 
                GAME_SOUNDS_AVAILABLE):
            logger.debug(f"\nGame sounds disabled - would have played: {game_event}\n")
            return
            
        # Check if sound player was successfully initialized
        if self.sound_player is None:
            logger.warning(f"\nSound player not available - cannot play: {game_event}\n")
            return
            
        if config.PLAYER_INTROS_ENABLED:
            if config.IGNORE_PREVIOUS_GAME_RESULTS_ON_FIRST_RUN and self.first_run:
                logger.debug(
                    "Per config, ignoring previous game on the first run, so no sound will be played")
                return
            try:
                self.sound_player.play_sound(game_event, logger)
            except Exception as e:
                logger.error(f"Error playing SC2 sound '{game_event}': {e}")
        else:
            logger.debug("SC2 player intros and other sounds are disabled")
    
    def safe_speak_text(self, text):
        """Safely call text-to-speech if available and enabled."""
        if (getattr(config, 'ENABLE_AUDIO', True) and 
            getattr(config, 'TEXT_TO_SPEECH', True) and 
            AUDIO_IMPORTS_AVAILABLE and 
            ts is not None):
            try:
                ts.speak_text(text)
            except Exception as e:
                logger.error(f"Error in text-to-speech: {e}")
        else:
            logger.debug(f"TTS disabled - would have said: {text}")

    # incorrect IDE warning here, keep parameters at 3
    def signal_handler(self, signal, frame):
        self.shutdown_flag = True
        logger.debug(
            "================================================SHUTTING DOWN BOT========================================")
        
        # Check if IRC connection exists before trying to disconnect
        if hasattr(self, 'connection') and self.connection:
            try:
                self.die("Shutdown requested.")
            except Exception as e:
                logger.error(f"Error during IRC disconnect: {e}")
        else:
            logger.info("No IRC connection to disconnect - shutting down directly")
        
        sys.exit(0)

    def listen_for_speech_whisperAI(self):
        # Safety check - don't run if STT imports aren't available
        if not STT_IMPORTS_AVAILABLE or sd is None or np is None:
            logger.warning("Speech-to-text not available - listen_for_speech_whisperAI exiting")
            return
            
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

                    print_indicator("o")
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
                        from openai import OpenAI
                        client = OpenAI(api_key=config.OPENAI_API_KEY)
                        with open(extended_filename, "rb") as audio_file:
                            response = client.audio.transcriptions.create(
                                model="whisper-1",
                                file=audio_file
                            )
                            partial_command = response.text.strip().lower()

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

                            # Process the "comments" command directly
                            if "player comments" in command:
                                logger.debug("Command recognized: 'player comments'")
                                self.safe_speak_text("Did you want to give your own comments about that player and last game?")

                                # Capture the player's comment
                                try:
                                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as comment_tmp_file:
                                        comment_filename = comment_tmp_file.name

                                    audio_data = sd.rec(int(chunk_duration * fs), samplerate=fs, channels=1, dtype='int16')
                                    sd.wait()
                                    wavfile.write(comment_filename, fs, audio_data)

                                    with open(comment_filename, "rb") as comment_audio_file:
                                        comment_response = client.audio.transcriptions.create(
                                            model="whisper-1",
                                            file=comment_audio_file
                                        )
                                        player_comment = comment_response.text.strip()

                                    os.remove(comment_filename)  # Clean up temporary file

                                    # Define specific invalid phrases
                                    invalid_phrases = [
                                        r"\bno thanks\b",
                                        r"\bno thank you\b",
                                        r"\bnope thanks\b"
                                    ]

                                    if player_comment and not any(re.search(pattern, player_comment.lower()) for pattern in invalid_phrases):
                                        logger.debug(f"Captured player comment: '{player_comment}'")
                                        if self.db.update_player_comments_in_last_replay(player_comment):
                                            self.safe_speak_text("Your comment has been added.")
                                        else:
                                            self.safe_speak_text("No recent replays found to update.")
                                    else:
                                        logger.debug(f"Ignored invalid or declined comment: '{player_comment}'")
                                        self.safe_speak_text("Comment not added.")

                                except Exception as e:
                                    logger.error(f"Error updating player comment in database: {e}")
                                    self.safe_speak_text("Failed to add your comment due to a system error.")
                                continue

                            # Process the full command
                            for keywords, responses in config.SPEECH2TEXT_OPTIONS:
                                if any(word in command for word in keywords):
                                    logger.debug(f"Command recognized: '{keywords[0]}' or similar")
                                    msg = str(responses[0]) if isinstance(responses, list) and len(responses) > 0 else str(responses)
                                    self.play_SC2_sound(keywords[0])
                                    chat_utils.processMessageForOpenAI(self, msg, "helpful", logger, contextHistory)
                                    contextHistory.clear()
                                    break

                            if "adios" in command:
                                logger.debug("Exit command recognized. Stopping the bot.")
                                self.shutdown_flag = True
                                self.die("Shutdown requested.")  # Ensure bot terminates
                                break

                        os.remove(temp_filename)  # Clean up temporary file
                    else:
                        os.remove(temp_filename)  # Clean up temporary file
                        continue
            except Exception as e:
                logger.error(f"Error during speech recognition: {e}")
                time.sleep(2)

    def listen_for_speech(self):
        # Safety check - don't run if STT imports aren't available
        if not STT_IMPORTS_AVAILABLE or sr is None:
            logger.warning("Speech-to-text not available - listen_for_speech exiting")
            return
            
        recognizer = sr.Recognizer()
        mic = sr.Microphone()
        msg = str("")

        with mic as source:
            recognizer.adjust_for_ambient_noise(source)
            while not self.shutdown_flag:
                try:
                    # Listen for the cue word "hey madison"
                    #logger.debug("Listening for 'hey madison' cue...")
                    print_indicator("o")
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
                        self.safe_speak_text("yes?")
                        
                        # Listen for the follow-up command
                        try:
                            audio = recognizer.listen(source, phrase_time_limit=2)
                            follow_up_command = recognizer.recognize_google(audio).lower()
                            logger.debug(f"Follow-up command: '{follow_up_command}'")

                            if "smile" in follow_up_command:
                                logger.debug("Command recognized: 'smile'")
                                # Add your handling code here
                                self.safe_speak_text("I'm smiling!")
                            else:
                                logger.debug(f"Unhandled follow-up command: '{follow_up_command}'")
                                self.safe_speak_text("I didn't understand that.")

                        except sr.UnknownValueError:
                            logger.debug("Could not understand the follow-up command.")
                            self.safe_speak_text("I didn't catch that.")
                        except sr.RequestError as e:
                            logger.error(f"Request error from speech recognition service: {e}")
                            time.sleep(2)
                        except Exception as e:
                            #logger.error(f"Error during speech recognition: {e}")
                            print_indicator("e")
                            time.sleep(2)
                    
                    else:
                        print_indicator("?")
                        
                except sr.UnknownValueError:
                    print_indicator("x")
                except sr.RequestError as e:
                    logger.error(f"Request error from speech recognition service: {e}")
                    time.sleep(2)  # Prevent rapid retries
                except Exception as e:
                    #logger.error(f"Error during speech recognition: {e}")
                    print_indicator("e")
                    time.sleep(2)  # Prevent rapid retries

    def monitor_game(self):
        previous_game = None
        heartbeat_counter = 0
        heartbeat_interval = config.HEARTBEAT_MYSQL  # Number of iterations before sending a heartbeat for MySQL
        
        # Check if SC2 monitoring is enabled
        sc2_monitoring_enabled = getattr(config, 'ENABLE_SC2_MONITORING', True)
        if not sc2_monitoring_enabled:
            logger.info("SC2 monitoring disabled - running in heartbeat-only mode for server deployment")

        while not self.shutdown_flag:
            # Only check SC2 status if monitoring is enabled
            if sc2_monitoring_enabled:
                try:
                    current_game = check_SC2_game_status(logger)
                    
                    if current_game and hasattr(current_game, 'get_status'):
                        if (current_game.get_status() == "MATCH_STARTED" or current_game.get_status() == "REPLAY_STARTED"):
                            self.conversation_mode = "in_game"
                        else:
                            self.conversation_mode = "normal"
                    else:
                        # If no game data, maintain normal conversation mode
                        self.conversation_mode = "normal"
                    if current_game:
                        # Check if this is a replay of someone else's game (not involving the streamer)
                        try:
                            # Only skip if watching replays of OTHER people's games
                            should_skip = False
                            if hasattr(current_game, 'isReplay') and current_game.isReplay and config.IGNORE_GAME_STATUS_WHILE_WATCHING_REPLAYS:
                                player_names = current_game.get_player_names()
                                player_accounts_lower = [name.lower() for name in config.SC2_PLAYER_ACCOUNTS]
                                streamer_is_playing = any(name.lower() in player_accounts_lower for name in player_names)
                                if not streamer_is_playing:
                                    should_skip = True
                            
                            if not should_skip:
                                # wait so abandoned games doesnt result in false data of 0 seconds
                                time.sleep(2)
                                handle_SC2_game_results(self, previous_game, current_game, contextHistory, logger)
                        except Exception as e:
                            logger.debug(f"Error processing game status: {e}")
                            try:
                                _print_indicator_summary()
                            except:
                                pass  # Don't let summary errors interfere with main error handling

                    previous_game = current_game

                except Exception as e:
                    # Only log unexpected errors, not SC2 API connection issues (already handled)
                    if "isReplay" not in str(e) and "HTTPConnectionPool" not in str(e):
                        logger.debug(f"Unexpected error in monitor_game loop: {e}")
                    # SC2 API connection errors are already logged by check_SC2_game_status
            else:
                # SC2 monitoring disabled - just maintain normal conversation mode
                self.conversation_mode = "normal"
                
            # Always sleep regardless of success or failure to maintain proper timing
            time.sleep(config.MONITOR_GAME_SLEEP_SECONDS)
            
            # Increment the heartbeat counter
            heartbeat_counter += 1

            # Check if it's time to send a heartbeat
            if heartbeat_counter >= heartbeat_interval:
                try:
                    self.db.keep_connection_alive()
                    heartbeat_counter = 0  # Reset the counter after sending the heartbeat
                    # heartbeat indicator
                    print_indicator("+")                        
                except Exception as e:
                    logger.error(f"Error during database heartbeat call: {e}")                       
            else:
                # heartbeat indicator - show SC2 API status if monitoring enabled
                if config.ENABLE_SC2_MONITORING:
                    # Check if SC2 API has recent failures
                    from api.sc2_game_utils import check_SC2_game_status
                    if hasattr(check_SC2_game_status, 'consecutive_failures') and check_SC2_game_status.consecutive_failures > 0:
                        print_indicator("o")  # SC2 API errors
                    else:
                        print_indicator(".")  # SC2 API working
                else:
                    print_indicator(".")  # Normal heartbeat when SC2 disabled

    # This is a callback method that is invoked when bot successfully connects to an IRC Server
    def on_welcome(self, connection, event):
        # Join the channel and say a greeting
        connection.join(self.channel)
        message_on_welcome(self, logger)

    # This function is a listerner whenever there is a publish message on twitch chat room
    def on_pubmsg(self, connection, event):
        
        #process the message sent by the viewers in the twitch chat room
        process_pubmsg(self, event, logger, contextHistory)

    def _prepare_game_data_for_comment(self, game_player_names, winning_players, losing_players, logger):
        """Prepare game data for the comment prompt"""
        try:
            game_data = {}
            
            # Get opponent info (case-insensitive comparison against all player accounts)
            player_names_list = [name.strip() for name in game_player_names.split(',')]
            player_accounts_lower = [name.lower() for name in config.SC2_PLAYER_ACCOUNTS]
            
            # Find opponent by excluding all streamer accounts
            opponent_names = [name for name in player_names_list if name.lower() not in player_accounts_lower]
            if opponent_names:
                game_data['opponent_name'] = opponent_names[0]
                
                # Try to get opponent race - prioritize replay data over current game state
                opponent_race = 'Unknown'
                try:
                    # First try from replay data (most reliable after game ends)
                    if hasattr(self, 'last_replay_data') and self.last_replay_data:
                        for player_key, player_data in self.last_replay_data.get('players', {}).items():
                            if player_data.get('name') == opponent_names[0]:
                                opponent_race = player_data.get('race', 'Unknown')
                                logger.debug(f"Got opponent race from replay data: {opponent_race}")
                                break
                    
                    # Fallback to current game state if replay data not available
                    if opponent_race == 'Unknown' and hasattr(self, 'current_game') and self.current_game:
                        opponent_race = self.current_game.get_player_race(opponent_names[0])
                        logger.debug(f"Got opponent race from current game: {opponent_race}")
                except Exception as e:
                    logger.debug(f"Could not get opponent race: {e}")
                    opponent_race = 'Unknown'
                
                game_data['opponent_race'] = opponent_race
            
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
            
            # Build order data (if available from replay summary)
            try:
                # Check if we have replay summary available
                if hasattr(self, 'last_replay_data') and self.last_replay_data:
                    # Try to read the replay summary file for build order data
                    import os
                    replay_summary_path = 'temp/replay_summary.txt'
                    if os.path.exists(replay_summary_path):
                        with open(replay_summary_path, 'r') as f:
                            summary_text = f.read()
                        
                        # Get opponent name to specifically extract their build order
                        opponent_name = game_data.get('opponent_name', None)
                        if not opponent_name:
                            logger.debug("No opponent name available - cannot extract build order")
                        else:
                            # Parse build order from summary text - ONLY for the opponent
                            build_data = []
                            in_opponent_build = False
                            current_player = None
                            
                            for line in summary_text.split('\n'):
                                line = line.strip()
                                if "Build Order (first set of steps):" in line:
                                    # Extract player name from line (e.g., "Zeaschling's Build Order...")
                                    current_player = line.split("'s")[0]
                                    # Check if this is the opponent's build (case-insensitive)
                                    if current_player.lower() == opponent_name.lower():
                                        in_opponent_build = True
                                        logger.debug(f"Found opponent's build order section for: {current_player}")
                                    else:
                                        in_opponent_build = False
                                    continue
                                elif in_opponent_build and line.startswith("Time:"):
                                    # Parse: "Time: 0:00, Name: Probe, Supply: 12"
                                    try:
                                        parts = line.split(", ")
                                        time_part = parts[0].split(": ")[1]  # "0:00"
                                        name_part = parts[1].split(": ")[1]  # "Probe"
                                        supply_part = parts[2].split(": ")[1]  # "12"
                                        
                                        # Convert time to seconds
                                        minutes, seconds = map(int, time_part.split(":"))
                                        time_seconds = minutes * 60 + seconds
                                        
                                        build_data.append({
                                            'supply': int(supply_part),
                                            'name': name_part,
                                            'time': time_seconds
                                        })
                                    except Exception as e:
                                        logger.debug(f"Could not parse build order line: {line} - {e}")
                                        continue
                                elif in_opponent_build and not line.startswith("Time:"):
                                    # End of opponent's build order section - stop parsing
                                    break
                            
                            if build_data:
                                game_data['build_order'] = build_data
                                logger.debug(f"Added {len(build_data)} build order steps to game data for opponent {opponent_name}")
                            else:
                                logger.debug(f"No build order data found for opponent {opponent_name} in replay summary")
                    else:
                        logger.debug("Replay summary file not found")
                        
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
    
    def _display_pattern_validation(self, game_data, logger):
        """Display pattern learning validation and store suggestion if confidence is high"""
        try:
            from api.ml_opponent_analyzer import get_ml_analyzer
            import settings.config as config
            
            opponent_name = game_data.get('opponent_name', 'Unknown')
            opponent_race = game_data.get('opponent_race', 'Unknown')
            result = game_data.get('result', 'Unknown')
            duration = game_data.get('duration', 'Unknown')
            map_name = game_data.get('map', 'Unknown')
            
            # Get ML analyzer and check for patterns
            analyzer = get_ml_analyzer()
            db_instance = getattr(self, 'db', None)
            
            # Check if this is a known opponent
            is_known_opponent = False
            if db_instance:
                opponent_record = db_instance.check_player_and_race_exists(opponent_name, opponent_race)
                is_known_opponent = opponent_record is not None
            
            # Run pattern matching against ALL learned patterns (not just this opponent)
            # Extract build order from game data
            build_order = game_data.get('build_order', [])
            matched_patterns = analyzer.match_build_against_all_patterns(build_order, opponent_race, logger)
            
            # Wrap in analysis_data structure for compatibility
            analysis_data = {
                'matched_patterns': matched_patterns
            } if matched_patterns else None
            
            # Extract opponent's build from replay
            build_summary = []
            if 'build_order' in game_data and game_data['build_order']:
                # Get opponent's build order
                build_order = game_data['build_order']
                unit_counts = {}
                for step in build_order:
                    unit_name = step.get('name', '')
                    if unit_name:
                        unit_counts[unit_name] = unit_counts.get(unit_name, 0) + 1
                
                # Format as "Unit x count"
                for unit, count in sorted(unit_counts.items(), key=lambda x: -x[1])[:10]:  # Top 10
                    if count > 1:
                        build_summary.append(f"{unit} x{count}")
                    else:
                        build_summary.append(unit)
            
            # Display validation report in stdout
            print("\n" + "=" * 60)
            print("🔍 PATTERN LEARNING VALIDATION")
            print("=" * 60)
            print(f"Opponent: {opponent_name} ({opponent_race}) - {'KNOWN' if is_known_opponent else 'NEW'}")
            print(f"Result: {result} | Duration: {duration} | Map: {map_name}")
            print()
            
            if build_summary:
                print("--- OPPONENT'S BUILD (from replay) ---")
                print(", ".join(build_summary))
                print()
            
            # Display pattern matching results
            if analysis_data:
                matched_patterns = analysis_data.get('matched_patterns', [])
                
                if matched_patterns:
                    # Get best match
                    best_match = matched_patterns[0]
                    similarity = best_match.get('similarity', 0) * 100
                    pattern_comment = best_match.get('comment', 'No description')
                    keywords = best_match.get('keywords', [])
                    
                    print(f"--- BEST PATTERN MATCH ({similarity:.0f}% similarity) ---")
                    print(f'Pattern: "{pattern_comment}"')
                    if keywords:
                        print(f"Keywords matched: {', '.join(keywords[:5])}")
                    print()
                    
                    # Check if confidence is high enough to suggest
                    if similarity >= config.PATTERN_SUGGESTION_MIN_SIMILARITY * 100:
                        # Store suggestion for Twitch chat handler
                        self.suggested_pattern_comment = pattern_comment
                        print("✓ High confidence match!")
                        print()
                        print("To accept, type in Twitch:  player comment yes")
                    else:
                        # Clear any previous suggestion
                        self.suggested_pattern_comment = None
                        print("⚠ Low confidence match - please provide custom comment")
                        print()
                        print("To add custom, type in Twitch:  player comment <your text>")
                else:
                    # No patterns matched
                    self.suggested_pattern_comment = None
                    print("--- NO PATTERN MATCH ---")
                    print("This build doesn't match existing patterns.")
                    print()
                    print("Please describe this strategy in Twitch:")
                    print("  player comment <your description>")
            else:
                # No analysis data (no patterns exist yet)
                self.suggested_pattern_comment = None
                print("--- NO PATTERNS AVAILABLE ---")
                print("Building pattern database - please add your first comment!")
                print()
                print("Type in Twitch:  player comment <your description>")
            
            print()
            print("To skip, don't type anything (DB will remain empty)")
            print("=" * 60)
            print()
            
        except Exception as e:
            logger.error(f"Error in pattern validation display: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")