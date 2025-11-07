from settings import config
import openai
import re
import random
import sys
import time
import math
from utils.emote_utils import get_random_emote
from utils.emote_utils import remove_emotes_from_message
import utils.wiki_utils as wiki_utils
import utils.tokensArray as tokensArray
import string
from models.mathison_db import Database

def clean_text_for_logging(text):
    """Clean text for logging by replacing problematic Unicode characters"""
    if not text:
        return text
    
    try:
        # Try to encode as ASCII, replacing problematic characters
        return text.encode('ascii', 'replace').decode('ascii')
    except:
        # Fallback: remove non-ASCII characters
        return ''.join(char if ord(char) < 128 else '?' for char in text)

# Conditional audio imports
try:
    if getattr(config, 'ENABLE_AUDIO', True):
        from api.text2speech import speak_text
        TTS_AVAILABLE = True
    else:
        TTS_AVAILABLE = False
        speak_text = None
except (ImportError, AttributeError):
    TTS_AVAILABLE = False
    speak_text = None 

# This function logs that the bot is starting with also logs some configurations of th bot
# This also sends random emoticon to twitch chat room
def message_on_welcome(self, logger):
    logger.debug(
        "================================================STARTING BOT========================================")
    bot_mode = "BOT MODES \n"
    bot_mode += "TEST_MODE: " + str(config.TEST_MODE) + "\n"
    bot_mode += "TEST_MODE_SC2_CLIENT_JSON: " + \
        str(config.TEST_MODE_SC2_CLIENT_JSON) + "\n"
    bot_mode += "PLAYER_INTROS_ENABLED: " + \
        str(config.PLAYER_INTROS_ENABLED) + "\n"
    bot_mode += "USE_WHISPER: " + \
        str(config.USE_WHISPER) + "\n"    
    bot_mode += "ANALYZE_REPLAYS_FOR_TEST: " + \
        str(config.USE_CONFIG_TEST_REPLAY_FILE) + "\n"
    bot_mode += "IGNORE_REPLAYS: " + \
        str(config.IGNORE_GAME_STATUS_WHILE_WATCHING_REPLAYS) + "\n"
    bot_mode += "IGNORE_PREVIOUS_GAME_RESULTS_ON_FIRST_RUN: " + \
        str(config.IGNORE_PREVIOUS_GAME_RESULTS_ON_FIRST_RUN) + "\n"
    bot_mode += "MONITOR_GAME_SLEEP_SECONDS: " + \
        str(config.MONITOR_GAME_SLEEP_SECONDS) + "\n"
    logger.debug(bot_mode)

    prefix = ""  # if any
    greeting_message = f'{prefix} {get_random_emote()}'
    msgToChannel(self, greeting_message, logger, send_to_discord=True)

def clean_text_for_chat(msg):
    # Combine carriage return and line feed replacement with filtering non-printable characters
    msg = ''.join(filter(lambda x: x in set(string.printable), msg.replace('\r', '').replace('\n', '')))
    return msg

# This function sends and logs the messages sent to twitch chat channel and optionally Discord
def msgToChannel(self, message, logger, text2speech=False, send_to_discord=False):

    # Clean up the message
    message = clean_text_for_chat(message)

    # Calculate the size of the message in bytes
    message_bytes = message.encode()
    message_size = len(message_bytes)

    # Log the byte size of the message
    logger.debug(f"Message size in bytes: {message_size}")

    # Check if the message exceeds the 512-byte limit
    if message_size > 512:
        truncated_message_bytes = message_bytes[:512 - len(" ... more".encode())] + " ... more".encode()
    else:
        truncated_message_bytes = message_bytes

    # Convert the truncated message back to a string
    truncated_message_str = truncated_message_bytes.decode()

    # Send to Twitch if this is a Twitch bot
    if hasattr(self, 'connection') and hasattr(self.connection, 'privmsg'):
        self.connection.privmsg(self.channel, truncated_message_str)
    
    # Send to Discord only if explicitly requested
    if send_to_discord:
        logger.debug("Checking Discord integration...")
        try:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from api.discord_bot import queue_message_for_discord
            
            discord_enabled = hasattr(config, 'DISCORD_ENABLED') and getattr(config, 'DISCORD_ENABLED', False)
            logger.debug(f"Discord enabled: {discord_enabled}")
            
            if discord_enabled:
                logger.info(f"Sending message to Discord: {truncated_message_str[:100]}...")
                # Simply queue the message for Discord
                queue_message_for_discord(truncated_message_str)
                logger.debug("Message queued for Discord successfully")
            else:
                logger.debug("Discord is disabled, skipping Discord send")
                
        except ImportError as e:
            logger.debug(f"Discord bot not available (ImportError): {e}")
        except Exception as e:
            logger.error(f"Discord integration error: {e}")
            logger.exception("Discord integration exception:")
    else:
        logger.debug("send_to_discord=False, skipping Discord send")
    
    logger.debug(
        "---------------------MSG TO CHANNEL----------------------")
    logger.debug(truncated_message_str)
    logger.debug(
        "---------------------------------------------------------")

    logger.debug(f"TEXT2SPEECH settings: Config: {config.TEXT_TO_SPEECH}, text2speech: {text2speech}")
    # Check if the keywords are present to override the settings
    override_speech = False
    if "player comments warning" in truncated_message_str:
        logger.debug("'player comments warning' detected, temporarily enabling text-to-speech.")
        override_speech = True  # Override for this instance
        # Replace "player comments warning" in a case-insensitive manner
        truncated_message_str = re.sub(r"player comments warning", "", truncated_message_str, flags=re.IGNORECASE).strip()

    # Determine whether to proceed with text-to-speech
    if override_speech or (config.TEXT_TO_SPEECH and text2speech):
        try:
            logger.debug("Preparing to speak the message.")

            # Process the message to remove emotes and add punctuation
            truncated_message_str = remove_emotes_from_message(truncated_message_str)
            truncated_message_str = "add commas, period and other appropriate punctuation: " + truncated_message_str

            # Generate the response using OpenAI
            completion = send_prompt_to_openai(truncated_message_str)
            if completion.choices[0].message is not None:
                logger.debug("completion.choices[0].message.content: " + completion.choices[0].message.content)
                response = completion.choices[0].message.content
                truncated_message_str = response

            # Speak the processed message if TTS is available
            if TTS_AVAILABLE and speak_text is not None:
                speak_text(truncated_message_str, mode=1)
            else:
                logger.debug(f"TTS not available - would have said: {truncated_message_str}")
        except Exception as e:
            logger.error(f"Error in text-to-speech: {e}")
        finally:
            logger.debug("Speech processing complete.")
    else:
        logger.debug("Text-to-speech is disabled. Skipping speech processing.")

        
# This function processes the message receive in twitch chat channel
# This will determine if the bot will reply base on dice roll
# And this will generate the response
def process_pubmsg(self, event, logger, contextHistory):
    # Print indicator summary before logging
    try:
        from api.twitch_bot import _print_indicator_summary
        _print_indicator_summary()
    except:
        pass

    logger.debug("processing pubmsg")

    # Get message from chat
    original_msg = event.arguments[0]
    msg = original_msg.lower()
    sender = event.source.split('!')[0]
    # tags = {kvpair["key"]: kvpair["value"] for kvpair in event.tags}
    # user = {"name": tags["display-name"], "id": tags["user-id"]}

    # Check for Y/N response to overwrite confirmation (must be before player comment check)
    if sender.lower() == config.PAGE.lower() and hasattr(self, 'pending_player_comment') and self.pending_player_comment:
        if msg.strip().lower() in ['y', 'yes']:
            logger.info("User confirmed overwrite of existing comment")
            try:
                pending = self.pending_player_comment
                comment_text = pending['comment']
                replay_info = pending['replay']
                
                # Overwrite the comment
                success = self.db.update_player_comments_in_last_replay(comment_text)
                
                if success and hasattr(self, 'pattern_learner') and self.pattern_learner:
                    game_data = {
                        'opponent_name': replay_info['opponent'],
                        'map': replay_info['map'],
                        'date': replay_info['date'],
                        'result': replay_info['result'],
                        'duration': replay_info['duration']
                    }
                    
                    self.pattern_learner._process_new_comment(game_data, comment_text)
                    self.pattern_learner.save_patterns_to_file()
                    
                    response = f"Overwritten comment for game vs {replay_info['opponent']} on {replay_info['map']} ({replay_info['date']}): '{comment_text}'"
                    msgToChannel(self, response, logger)
                else:
                    msgToChannel(self, "Failed to save comment", logger)
                    
            except Exception as e:
                logger.error(f"Error overwriting comment: {e}")
                msgToChannel(self, f"Error saving comment: {str(e)}", logger)
            finally:
                self.pending_player_comment = None
            return
            
        elif msg.strip().lower() in ['n', 'no']:
            logger.info("User declined overwrite, checking for newer replay")
            try:
                pending = self.pending_player_comment
                original_timestamp = pending['timestamp']
                comment_text = pending['comment']
                
                # Get latest replay again to see if new game happened
                latest_replay = self.db.get_latest_replay()
                
                if not latest_replay:
                    msgToChannel(self, "No replays found", logger)
                elif latest_replay['timestamp'] > original_timestamp:
                    # New game exists!
                    if latest_replay.get('existing_comment'):
                        msgToChannel(self, f"Newer replay vs {latest_replay['opponent']} also has a comment - cannot save", logger)
                    else:
                        # Save to new replay
                        success = self.db.update_player_comments_in_last_replay(comment_text)
                        
                        if success and hasattr(self, 'pattern_learner') and self.pattern_learner:
                            game_data = {
                                'opponent_name': latest_replay['opponent'],
                                'map': latest_replay['map'],
                                'date': latest_replay['date'],
                                'result': latest_replay['result'],
                                'duration': latest_replay['duration']
                            }
                            
                            self.pattern_learner._process_new_comment(game_data, comment_text)
                            self.pattern_learner.save_patterns_to_file()
                            
                            response = f"Saved comment to newer game vs {latest_replay['opponent']} on {latest_replay['map']} ({latest_replay['date']}): '{comment_text}'"
                            msgToChannel(self, response, logger)
                        else:
                            msgToChannel(self, "Failed to save comment to newer replay", logger)
                else:
                    # No new game
                    msgToChannel(self, "No new empty replay found - comment not saved", logger)
                    
            except Exception as e:
                logger.error(f"Error handling no response: {e}")
                msgToChannel(self, f"Error: {str(e)}", logger)
            finally:
                self.pending_player_comment = None
            return

    # Handle player comments from channel owner via Twitch chat
    if msg.startswith('player comment') and sender.lower() == config.PAGE.lower():
        logger.info(f"Player comment received from {sender} in Twitch chat")
        
        # Extract comment text after "player comment" or "player comments"
        if original_msg.lower().startswith('player comments '):
            comment_text = original_msg[16:].strip()  # "player comments " = 16 chars
        elif original_msg.lower().startswith('player comment '):
            comment_text = original_msg[15:].strip()  # "player comment " = 15 chars
        else:
            msgToChannel(self, "Usage: player comment <your comment text>", logger)
            return
        
        if not comment_text:
            msgToChannel(self, "Please provide comment text after 'player comment'", logger)
            return
        
        try:
            # Get the latest replay from database
            latest_replay = self.db.get_latest_replay()
            
            if not latest_replay:
                msgToChannel(self, "No replays found in database - please play a game first", logger)
                return
            
            opponent = latest_replay.get('opponent', 'Unknown')
            map_name = latest_replay.get('map', 'Unknown')
            game_date = latest_replay.get('date', 'Unknown')
            existing_comment = latest_replay.get('existing_comment')
            
            # Check if comment already exists
            if existing_comment:
                # Store pending state for Y/N confirmation
                self.pending_player_comment = {
                    'comment': comment_text,
                    'replay': latest_replay,
                    'timestamp': latest_replay['timestamp']
                }
                
                response = f"There is already data there for last game vs {opponent} on {map_name} ({game_date}). Are you sure you want to overwrite it? Y/N"
                msgToChannel(self, response, logger)
                return
            
            # No existing comment - save directly
            if hasattr(self, 'pattern_learner') and self.pattern_learner:
                # Update database with player comment
                success = self.db.update_player_comments_in_last_replay(comment_text)
                
                if success:
                    # Process comment for pattern learning
                    game_data = {
                        'opponent_name': opponent,
                        'map': map_name,
                        'date': game_date,
                        'result': latest_replay.get('result', 'Unknown'),
                        'duration': latest_replay.get('duration', 'Unknown')
                    }
                    
                    self.pattern_learner._process_new_comment(game_data, comment_text)
                    self.pattern_learner.save_patterns_to_file()
                    
                    response = f"Saved comment for game vs {opponent} on {map_name} ({game_date}): '{comment_text}'"
                    logger.info(response)
                    msgToChannel(self, response, logger)
                else:
                    msgToChannel(self, f"Failed to save comment to database for {opponent} on {map_name}", logger)
            else:
                msgToChannel(self, "Pattern learning system not available", logger)
                
        except Exception as e:
            logger.error(f"Error saving player comment from Twitch: {e}")
            import traceback
            logger.error(traceback.format_exc())
            msgToChannel(self, f"Error saving comment: {str(e)}", logger)
        
        return

    if 'commands' in msg.lower():
        response = f"{config.BOT_COMMANDS}"
        response = clean_text_for_chat(response)
        trimmed_msg = tokensArray.truncate_to_byte_limit(response, config.TWITCH_CHAT_BYTE_LIMIT)        
        msgToChannel(self, trimmed_msg, logger)
        return

    # Send response to direct msg or keyword which includes Mathison being mentioned
    if 'open sesame' in msg.lower() or any(sub.lower() == msg.lower() for sub in config.OPEN_SESAME_SUBSTITUTES):
        logger.debug("received open sesame: " + str(msg.lower()))
        processMessageForOpenAI(self, msg, self.conversation_mode, logger, contextHistory)
        return

    # search wikipedia
    if 'wiki' in msg.lower():
        logger.debug("received wiki command: /n" + msg)
        msg = wiki_utils.wikipedia_question(msg, self)
        logger.debug("wiki answer: /n" + msg)
        trimmed_msg = tokensArray.truncate_to_byte_limit(msg, config.TWITCH_CHAT_BYTE_LIMIT)        
        trimmed_msg = "restate all the info, do not ommit any details: " + trimmed_msg
        processMessageForOpenAI(self, trimmed_msg, self.conversation_mode, logger, contextHistory)
        return

    # search replays DB
    if 'career' in msg.lower():
        contextHistory.clear()
        logger.debug("received career record command: \n" + msg)
        player_name = msg.split(" ", 1)[1]
        career_record = self.db.get_player_overall_records(player_name)
        logger.debug("career overall record answer: \n" + career_record)          
        career2_record = self.db.get_player_race_matchup_records(player_name)        
        logger.debug("career matchups record answer: \n" + career_record)    
        career_record = career_record + " " + career2_record      

        # Check if there are any results
        if career_record:

            trimmed_msg = tokensArray.truncate_to_byte_limit(career_record, config.TWITCH_CHAT_BYTE_LIMIT)
            msg = f'''
                Review this example:

                    when given a player, DarkMenace the career records are:

                        Overall matchup records for darkmenace: 425 wins - 394 losses Race matchup records for darkmenace: Protoss vs Protoss: 15 wins - 51 lossesProtoss vs Terran: 11 wins - 8 lossesProtoss vs Zerg: 1 wins - 1 lossesTerran vs Protoss: 8 wins - 35 lossesTerran vs Terran: 3 wins - 1 lossesTerran vs Zerg: 4 wins - 3 lossesZerg vs Protoss: 170 wins - 137 lossesZerg vs Terran: 138 wins - 100 lossesZerg vs Zerg: 75 wins - 58 losses

                    From the above, say it exactly like this format:

                        overall: 425-394, each matchup: PvP: 15-51 PvT: 11-8 PvZ: 1-1 TvP: 8-35 TvT: 3-1 TvZ: 4-3 ZvP: 170-137 ZvT: 138-100 ZvZ: 75-58

                Now do the same but only using this data:

                    {player_name} : {trimmed_msg}.

                Then add a 10 word comment about the matchup, after.
            '''
            
        else:
            msg = f"Restate all of the info here: There is no career games that I know for {player_name} ."

        # Send the message for processing
        # processMessageForOpenAI(self, msg, self.conversation_mode, logger, contextHistory)
        
        # no mathison flavoring, just raw send to prompt
        completion = send_prompt_to_openai(msg)
        if completion.choices[0].message is not None:
            logger.debug(
                "completion.choices[0].message.content: " + completion.choices[0].message.content)
        response = completion.choices[0].message.content

        if len(response) >= 400:
            logger.debug(
                f"Chunking response since it's {len(response)} characters long")

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
                msgToChannel(self, chunk, logger)

        else:            
            msgToChannel(self, response, logger)
        return

    # search replays DB
    if 'history' in msg.lower():
        contextHistory.clear()
        logger.debug("received history command: /n" + msg)
        player_name = msg.split(" ", 1)[1]
        history_list = self.db.get_player_records(player_name)
        logger.debug("history answer: /n" + str(history_list))  

        # Process each record and format it as desired
        formatted_records = [f"{rec.split(', ')[0]} vs {rec.split(', ')[1]}, {rec.split(', ')[2].split(' ')[0]}-{rec.split(', ')[3].split(' ')[0]}" for rec in history_list]

        # Join the formatted records into a single string
        result_string = " and ".join(formatted_records)

        trimmed_msg = tokensArray.truncate_to_byte_limit(result_string, config.TWITCH_CHAT_BYTE_LIMIT)
        # if history_list is empty then msg is "no records found"
        if history_list == []:
            msg = (f"restate all of the info here: there are no game records in history for {player_name}")
        else:
            msg = (f"restate all of the info here and do not exclude anything: total win/loss record of {player_name} we know the results of so far {trimmed_msg}")
        #msgToChannel(self, msg, logger)
        processMessageForOpenAI(self, msg, self.conversation_mode, logger, contextHistory)
        return
  
    def chunk_list(lst, max_chunk_size):
        """Splits the list into smaller lists each having a length less than or equal to max_chunk_size."""
        for i in range(0, len(lst), max_chunk_size):
            yield lst[i:i + max_chunk_size]

    # Check if the message contains "games in" and "hours"
    if 'games in' in msg.lower() and 'hours' in msg.lower():
        logger.debug("Received command to fetch games in the last X hours")

        # Use regex to extract the number of hours from the message
        match = re.search(r'games in (the )?last (\d+) hours', msg.lower())
        if match:
            hours = int(match.group(2))  # Extract the number of hours
        else:
            hours = 4  # Default value if no number is found

        if hours > 72:
            hours = 72  # Max number of hours allowed is 72

        # Retrieve games for the last X hours
        recent_games = self.db.get_games_for_last_x_hours(hours)
        logger.debug(f"Games in the last {hours} hours: \n" + str(recent_games))

        # Process each game record and format it as desired
        formatted_records = [f"{game}" for game in recent_games]

        # Define chunk size based on an estimated average size of each record
        avg_record_size = 100  # This is an estimation; you might need to adjust it
        max_chunk_size = config.TWITCH_CHAT_BYTE_LIMIT // avg_record_size

        msg = f"Games played in the last {hours} hours are: "
        msgToChannel(self, msg, logger)
        
        # Split the formatted records into chunks
        for chunk in chunk_list(formatted_records, max_chunk_size):
            # Join the records in the chunk into a single string
            chunk_string = " and ".join(chunk)

            # Truncate the chunk string to byte limit
            trimmed_msg = tokensArray.truncate_to_byte_limit(chunk_string, config.TWITCH_CHAT_BYTE_LIMIT)

            # Send the chunk message
            msgToChannel(self, trimmed_msg, logger)
            # processMessageForOpenAI(self, msg, self.conversation_mode, logger, contextHistory)

    # Function to process the 'head to head' command
    if 'head to head' in msg.lower():
        contextHistory.clear()
        logger.debug(f"Received 'head to head' command: \n{msg}")

        # Use regular expression to extract player names
        match = re.search(r"head to head (\w+) (\w+)", msg.lower())
        if match:
            player1_name, player2_name = match.groups()

            # Retrieve head-to-head records
            head_to_head_list = self.db.get_head_to_head_matchup(player1_name, player2_name)
            logger.debug(f"Type of head_to_head_list: {type(head_to_head_list)}")
            logger.debug(f"Head to head answer: \n{str(head_to_head_list)}")

            # Check if there are any results
            if head_to_head_list:
                # Since the records are already formatted, join them into a single string
                result_string = ", ".join(head_to_head_list)

                trimmed_msg = tokensArray.truncate_to_byte_limit(result_string, config.TWITCH_CHAT_BYTE_LIMIT)
                msg = f'''
                    Review this example:

                        when given 2 player, DarkMenace vs KJ the records are:

                            ['DarkMenace (Terran) vs KJ (Zerg), 29 wins - 7 wins', 'DarkMenace (Protoss) vs KJ (Zerg), 9 wins - 12 wins', 'DarkMenace (Zerg) vs KJ (Zerg), 3 wins - 2 wins', 'DarkMenace (Protoss) vs KJ (Terran), 6 wins - 1 wins', 'DarkMenace (Terran) vs KJ (Terran), 1 wins - 0 wins', 'DarkMenace (Protoss) vs KJ (Protoss), 2 wins - 2 wins']

                        From the above, say it exactly like this format:

                            overall: 50-24, each matchup: TvZ 29-7, PvZ 9-12, ZvZ 3-2, PvT 6-1, TvT 1-0, PvP, 2-2.  Summary: <10 word comment about the matchup>

                    Now do the same but only using this data:

                        {player1_name} vs {player2_name}: {result_string}.

                    Then add a 10 word comment about the matchup, after.
                '''
                
            else:
                msg = f"Restate all of the info here: There are no head-to-head game records between {player1_name} and {player2_name} ."

            # Send the message for processing
            # processMessageForOpenAI(self, msg, self.conversation_mode, logger, contextHistory)
            
            # no mathison flavoring, just raw send to prompt
            completion = send_prompt_to_openai(msg)
            if completion.choices[0].message is not None:
                logger.debug(
                    "completion.choices[0].message.content: " + completion.choices[0].message.content)
            response = completion.choices[0].message.content

            if len(response) >= 400:
                logger.debug(
                    f"Chunking response since it's {len(response)} characters long")

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
                    msgToChannel(self, chunk, logger)

            else:            
                msgToChannel(self, response, logger)
           
        else:
            logger.debug("Invalid 'head to head' command format or player names not found.")
            # Optionally send an error message to the channel or log it.
        return

    # ignore certain users
    logger.debug("checking user: " + sender + " against ignore list")
    if sender.lower() in [user.lower() for user in config.IGNORE]:
        logger.debug("ignoring user: " + sender)
        return
    else:
        logger.debug("allowed user: " + sender)

    if config.PERSPECTIVE_DISABLED:
        logger.debug("google perspective config is disabled")
        toxicity_probability = 0
    else:
        toxicity_probability = tokensArray.get_toxicity_probability(
            msg, logger)
    # do not send toxic messages to openAI
    if toxicity_probability < config.TOXICITY_THRESHOLD:

        # any user greets via config keywords will be responded to
        if any(greeting in msg.lower() for greeting in config.GREETINGS_LIST_FROM_OTHERS):
            response = f"Hi {sender}!"
            response = f'{response} {get_random_emote()}'
            msgToChannel(self, response, logger)
            # disable the return - sometimes it matches words so we want mathison to reply anyway
            # DO NOT return

        if 'bye' in msg.lower():
            response = f"byers {sender}!"
            msgToChannel(self, response, logger)
            return

        if 'gg' in msg.lower():
            response = f"HSWP"
            msgToChannel(self, response, logger)
            return

        if 'bracket' in msg.lower() or '!b' in msg.lower() or 'FSL' in msg.upper() or 'fsl' in msg.lower():
            msg = f"Restate this including the full URL: This is the tournament info {config.BRACKET}"
            processMessageForOpenAI(self, msg, self.conversation_mode, logger, contextHistory)
            return

        # will only respond to a certain percentage of messages per config
        diceRoll = random.randint(0, 100) / 100
        logger.debug("rolled: " + str(diceRoll) +
                        " settings: " + str(config.RESPONSE_PROBABILITY))
        if diceRoll >= config.RESPONSE_PROBABILITY:
            logger.debug("will not respond")
            return

        processMessageForOpenAI(self, msg, self.conversation_mode, logger, contextHistory)
    else:
        response = random.randint(1, 3)
        switcher = {
            1: f"{sender}, please refrain from sending toxic messages.",
            2: f"Woah {sender}! Strong language",
            3: f"Calm down {sender}. What's with the attitude?"
        }
        msgToChannel(self, switcher.get(response), logger)

def send_prompt_to_openai(msg):
    """
    Send a given message as a prompt to OpenAI and return the response.

    :param msg: The message to send to OpenAI as a prompt.
    :return: The response from OpenAI.
    """
    from openai import OpenAI
    
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    completion = client.chat.completions.create(
        model=config.ENGINE,
        messages=[
            {"role": "user", "content": msg}
        ]
    )
    return completion

def process_ai_message(user_message, conversation_mode="normal", contextHistory=None, platform="twitch", logger=None):
    """
    Platform-agnostic AI message processing.
    Returns the AI response without platform-specific handling.
    """
    if contextHistory is None:
        contextHistory = []
    
    if logger is None:
        import logging
        logger = logging.getLogger(__name__)

    # let's give these requests some breathing room
    time.sleep(config.MONITOR_GAME_SLEEP_SECONDS)

    # remove open sesame
    msg = user_message.replace('open sesame', '')
    logger.debug(
        "----------------------------------------NEW MESSAGE FOR OPENAI-----------------------------------------")
    logger.debug(
        'msg omitted in log, to see it, look in: "sent to OpenAI"')

    # remove quotes
    msg = msg.replace('"', '')
    msg = msg.replace("'", '')

    # add line break to ensure separation
    msg = msg + "\n"

    # check tokensize
    total_tokens = tokensArray.num_tokens_from_string(
        msg, config.TOKENIZER_ENCODING)
    msg_length = len(msg)
    logger.debug(f"string length: {msg_length}, {total_tokens} tokens")

    # Trim message if too long
    if int(total_tokens) > config.CONVERSATION_MAX_TOKENS:
        divided_by = math.ceil(len(msg) // config.CONVERSATION_MAX_TOKENS)
        logger.debug(
            f"msg is too long so we are truncating it 1/{divided_by} of its length")
        msg = msg[0:msg_length // divided_by]
        msg = msg + "\n"  # add line break to ensure separation
        total_tokens = tokensArray.num_tokens_from_string(
            msg, config.TOKENIZER_ENCODING)
        msg_length = len(msg)
        logger.debug(
            f"new string length: {msg_length}, {total_tokens} tokens")

    # add User msg to conversation context if not replay nor last time played analysis
    if conversation_mode not in ["replay_analysis", "last_time_played"]:
        # add User msg to conversation context
        tokensArray.add_new_msg(
            contextHistory, 'User: ' + msg + "\n", logger)
        logger.debug("adding msg to context history")
    else:
        contextHistory.clear()

    if conversation_mode == "last_time_played":
        # no mood / perspective
        pass
    else:
        # add complete array as msg to OpenAI
        msg = msg + \
            tokensArray.get_printed_array("reversed", contextHistory)
        
        # Choose a random mood and perspective from the selected options
        selected_moods = [config.MOOD_OPTIONS[i] for i in config.BOT_MOODS]
        mood = random.choice(selected_moods)

        if conversation_mode == "replay_analysis":
            # say cutoff is 4, then select indices 0-3
            perspective_indices = config.BOT_PERSPECTIVES[:config.PERSPECTIVE_INDEX_CUTOFF]
        else:
            # Select indices 4-onwards
            perspective_indices = config.BOT_PERSPECTIVES[config.PERSPECTIVE_INDEX_CUTOFF:]

        selected_perspectives = [
            config.PERSPECTIVE_OPTIONS[i] for i in perspective_indices]
        perspective = random.choice(selected_perspectives)

        if (conversation_mode == "normal"):
            # if contextHistory has > 15 tuples, clear it
            if len(contextHistory) > 15:
                logger.debug(f"contextHistory has more than 15 tuples, clearing it")  
                contextHistory.clear()
            else:
                pass
            # Mathison is an AI bot watching the stream with everyone else, not referencing the streamer
            msg = (f"As a {mood} AI bot named Mathison watching this StarCraft 2 stream, {perspective}, "
                    + msg)
        else:
            if (conversation_mode == "in_game"):
                msg = (f"As a {mood} observer of matches in StarCraft 2, {perspective}, comment on this statement: "
                        + msg)
            else:
                if conversation_mode == "replay_analysis":
                    msg = (f"As a {mood} observer of matches in StarCraft 2, {perspective}. "
                            + "IMPORTANT: Use ONLY the Winners/Losers data provided - do NOT make assumptions about who won. "
                            + msg)
                else:
                    msg = (f"As a {mood} observer of matches in StarCraft 2, {perspective}, "
                            + msg)

    logger.debug("CONVERSATION MODE: " + conversation_mode)
    logger.debug("sent to OpenAI: %s", clean_text_for_logging(msg))

    completion = send_prompt_to_openai(msg)

    try:
        if completion.choices[0].message is not None:
            logger.debug(
                "completion.choices[0].message.content: " + completion.choices[0].message.content)
            response = completion.choices[0].message.content

            # add emote
            if random.choice([True, False]):
                response = f'{response} {get_random_emote()}'

            logger.debug('raw response from OpenAI:')
            logger.debug(clean_text_for_logging(response))

            # Clean up response
            # Remove carriage returns, newlines, and tabs
            response = re.sub('[\r\n\t]', ' ', response)
            # Remove non-ASCII characters
            response = re.sub('[^\x00-\x7F]+', '', response)
            response = re.sub(' +', ' ', response)  # Remove extra spaces
            response = response.strip()  # Remove leading and trailing whitespace

            # dont make it too obvious its a bot
            response = response.replace("As an AI language model, ", "")
            response = response.replace("User: , ", "")
            response = response.replace("Observer: , ", "")
            response = response.replace("Player: , ", "")

            logger.debug("cleaned up message from OpenAI:")
            # replace with ? all non ascii characters that throw an error in logger
            response = tokensArray.replace_non_ascii(response, replacement='?')
            logger.debug(clean_text_for_logging(response))

            # Remove all occurrences of "AI: "
            response = re.sub(r'\bAI: ', '', response)
            
            # Add AI response to conversation context
            tokensArray.add_new_msg(
                contextHistory, 'AI: ' + response + "\n", logger)

            logger.debug(f'AI response generated: {clean_text_for_logging(response)}')
            
            # For replay analysis, validate that the response doesn't contradict the actual game results
            if conversation_mode == "replay_analysis" and "Winners:" in msg and "Losers:" in msg:
                # Extract winners and losers from the original message
                winners_line = [line for line in msg.split('\n') if line.startswith('Winners:')]
                losers_line = [line for line in msg.split('\n') if line.startswith('Losers:')]
                
                if winners_line and losers_line:
                    winners = winners_line[0].replace('Winners:', '').strip()
                    losers = losers_line[0].replace('Losers:', '').strip()
                    
                    # Check if AI response contradicts the actual results
                    if winners and losers:
                        response_lower = response.lower()
                        winners_lower = winners.lower()
                        losers_lower = losers.lower()
                        
                        # If AI says loser won, fix it
                        if losers_lower in response_lower and "win" in response_lower and "victory" in response_lower:
                            logger.warning(f"AI hallucinated wrong winner! Said {losers} won when {winners} actually won. Fixing response.")
                            response = response.replace(f"{losers} won", f"{winners} won")
                            response = response.replace(f"{losers} victory", f"{winners} victory")
                            response = response.replace(f"{losers} took", f"{winners} took")
                        
                        # If AI says winner lost, fix it  
                        if winners_lower in response_lower and "loss" in response_lower and "defeat" in response_lower:
                            logger.warning(f"AI hallucinated wrong loser! Said {winners} lost when {losers} actually lost. Fixing response.")
                            response = response.replace(f"{winners} lost", f"{losers} lost")
                            response = response.replace(f"{winners} defeat", f"{losers} defeat")
            
            logger.debug(
                f'Conversation in context so far: {tokensArray.get_printed_array("reversed", contextHistory)}')
            
            return response

        else:
            response = 'oops, I have no response to that'
            logger.debug('Failed to generate response: %s', response)
            return response
            
    except Exception as e:
        logger.error('Failed to generate response: %s', e)
        return 'oops, I have no response to that'

def processMessageForOpenAI(self, msg, conversation_mode, logger, contextHistory):
    """
    Legacy function for Twitch bot compatibility.
    Now uses the platform-agnostic process_ai_message function.
    """
    
    # Use the new platform-agnostic function
    response = process_ai_message(msg, conversation_mode, contextHistory, "twitch", logger)
    
    if len(response) >= 400:
        logger.debug(
            f"Chunking response since it's {len(response)} characters long")

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
            msgToChannel(self, chunk, logger)
            # Log relevant details
            logger.debug(f'Sending openAI response chunk: {clean_text_for_logging(chunk)}')
    else:
        # if response is less than 150 characters
        if len(response) <= 150:
            # really short messages get to be spoken
            msgToChannel(self, response, logger, text2speech=True)
        else:
            msgToChannel(self, response, logger)                                        

        # Log relevant details
        logger.debug(f'AI msg to chat: {response}')