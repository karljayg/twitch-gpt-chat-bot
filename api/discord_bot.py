import discord
from discord.ext import commands
import logging
import asyncio
import queue
import threading
from datetime import datetime, timedelta
from settings import config
from api.chat_utils import clean_text_for_chat
import utils.tokensArray as tokensArray

logger = logging.getLogger(__name__)

# Global message queue for sending messages to Discord
message_queue = queue.Queue()

class DiscordBot(commands.Bot):
    def __init__(self, twitch_bot_ref=None):
        intents = discord.Intents.default()
        # Enable message content intent to read Discord messages (required for message content access)
        intents.message_content = True
        
        super().__init__(command_prefix='!', intents=intents)
        
        # Reference to Twitch bot for shared functionality
        self.twitch_bot = twitch_bot_ref
        self.channel_id = None
        
        # Share context history with Twitch bot for consistent AI responses
        self.contextHistory = []
        if twitch_bot_ref:
            self.contextHistory = twitch_bot_ref.contextHistory if hasattr(twitch_bot_ref, 'contextHistory') else []
        
        # Track messages for last word feature - stores message metadata for reply detection
        self.message_tracker = {}  # {message_id: {'timestamp': datetime, 'has_replies': bool, 'content': str, 'author': str}}
        self.last_processed_message_time = None  # Track the timestamp of the last message we replied to (prevents re-processing)
        
        # Background task for last word feature (will be started after on_ready)
        self.last_word_task = None

    async def on_ready(self):
        """Called when the bot is ready."""
        # Use the same logger as the Twitch bot
        from api.twitch_bot import logger as twitch_logger
        
        twitch_logger.info(f'=== DISCORD BOT CONNECTED ===')
        twitch_logger.info(f'Bot user: {self.user}')
        twitch_logger.info(f'Bot ID: {self.user.id}')
        twitch_logger.info(f'Connected to {len(self.guilds)} guilds')
        
        # Set the channel to monitor based on config
        if config.DISCORD_CHANNEL_ID:
            self.channel_id = config.DISCORD_CHANNEL_ID
            twitch_logger.info(f'Looking for channel ID: {self.channel_id}')
            channel = self.get_channel(self.channel_id)
            if channel:
                twitch_logger.info(f'Found Discord channel: {channel.name} in guild: {channel.guild.name}')
                # Send the same random emoji greeting as Twitch bot to announce presence
                from utils.emote_utils import get_random_emote
                greeting_message = get_random_emote()
                try:
                    await channel.send(greeting_message)
                    twitch_logger.info(f'Sent greeting message to Discord channel')
                except Exception as e:
                    twitch_logger.error(f'Failed to send greeting message: {e}')
                
                # Start the message processing task (handles queued messages from Twitch bot)
                twitch_logger.info('Starting message queue processor...')
                self.message_queue_task = self.loop.create_task(self.process_message_queue())
                
                # Start the last word checker task if enabled (ensures bot gets last word in conversations)
                if getattr(config, 'DISCORD_LAST_WORD_ENABLED', True):
                    twitch_logger.info('Starting last word checker...')
                    self.last_word_task = self.loop.create_task(self.last_word_checker_loop())
            else:
                # Debug info: list all available channels if target not found
                twitch_logger.error(f'Could not find Discord channel with ID: {self.channel_id}')
                twitch_logger.info('Available channels:')
                for guild in self.guilds:
                    twitch_logger.info(f'  Guild: {guild.name}')
                    for ch in guild.channels:
                        twitch_logger.info(f'    Channel: {ch.name} (ID: {ch.id}) Type: {type(ch)}')
        else:
            twitch_logger.error("No Discord channel ID configured")

    async def last_word_checker_loop(self):
        """Configurable loop to check for messages that haven't been replied to and need the bot's 'last word'.
        
        This feature ensures the bot gets the last word in conversations that have gone silent.
        It only responds to the most recent unreplied message to avoid spam.
        Timing is fully configurable via DISCORD_LAST_WORD_CHECK_FREQUENCY_HOURS and DISCORD_LAST_WORD_TIMEOUT_HOURS.
        """
        await self.wait_until_ready()  # Wait until bot is ready
        
        try:
            while not self.is_closed():
                try:
                    await self.last_word_checker()
                    
                    # Use configurable check frequency (how often to scan for unreplied messages)
                    check_frequency_hours = getattr(config, 'DISCORD_LAST_WORD_CHECK_FREQUENCY_HOURS', 1)
                    check_frequency_seconds = check_frequency_hours * 3600
                    await asyncio.sleep(check_frequency_seconds)
                    
                except asyncio.CancelledError:
                    # Task was cancelled (likely due to shutdown) - break gracefully
                    try:
                        from api.twitch_bot import logger as twitch_logger
                        twitch_logger.info("Last word checker loop cancelled - shutting down gracefully")
                    except:
                        logger.info("Last word checker loop cancelled - shutting down gracefully")
                    raise  # Re-raise to properly handle the cancellation
                    
                except Exception as e:
                    try:
                        from api.twitch_bot import logger as twitch_logger
                        twitch_logger.error(f"Error in last word checker loop: {e}")
                        # Wait a bit before retrying on error to avoid spam on persistent issues
                        await asyncio.sleep(300)  # 5 minutes
                    except:
                        logger.error(f"Error in last word checker loop: {e}")
                        await asyncio.sleep(300)
                        
        except asyncio.CancelledError:
            # Final cancellation handling - ensure we exit cleanly
            try:
                from api.twitch_bot import logger as twitch_logger
                twitch_logger.info("Last word checker loop task cancelled during shutdown")
            except:
                logger.info("Last word checker loop task cancelled during shutdown")
            # Don't re-raise here - let the task end gracefully

    async def last_word_checker(self):
        """Check for messages that haven't been replied to and need the bot's 'last word'."""
        if not getattr(config, 'DISCORD_LAST_WORD_ENABLED', True):
            return
            
        try:
            from api.twitch_bot import logger as twitch_logger
            
            timeout_hours = getattr(config, 'DISCORD_LAST_WORD_TIMEOUT_HOURS', 3)
            check_frequency_hours = getattr(config, 'DISCORD_LAST_WORD_CHECK_FREQUENCY_HOURS', 1)
            
            twitch_logger.debug(f"Last word checker running - timeout: {timeout_hours}h, frequency: {check_frequency_hours}h")
            
            cutoff_time = datetime.now() - timedelta(hours=timeout_hours)
            
            # Find unreplied messages that are old enough AND newer than our last processed message
            # This prevents re-processing the same messages and ensures we only get new unreplied messages
            candidate_messages = []
            messages_to_remove = []
            
            for message_id, data in self.message_tracker.items():
                # Clean up very old messages (older than timeout threshold)
                if data['timestamp'] < cutoff_time:
                    messages_to_remove.append(message_id)
                    
                    # Check if this is an unreplied user message that we haven't processed yet
                    # Conditions: no replies, not from bot, not already replied to by bot, newer than last processed
                    if (not data['has_replies'] and 
                        not data.get('bot_replied', False) and 
                        data.get('author') != 'BOT' and
                        (self.last_processed_message_time is None or data['timestamp'] > self.last_processed_message_time)):
                        candidate_messages.append((message_id, data))
            
            # Clean up old messages to prevent memory bloat
            for message_id in messages_to_remove:
                del self.message_tracker[message_id]
            
            # Reply to the MOST RECENT unreplied message only (prevents spam from old message backlog)
            if candidate_messages and self.channel_id:
                # Sort by timestamp to get the most recent message (most relevant to current conversation)
                candidate_messages.sort(key=lambda x: x[1]['timestamp'], reverse=True)
                message_id, data = candidate_messages[0]  # Take the most recent
                
                channel = self.get_channel(self.channel_id)
                if channel:
                    try:
                        original_message = await channel.fetch_message(message_id)
                        twitch_logger.info(f"Last word checker found {len(candidate_messages)} unreplied messages, responding to the most recent from {data['author']}...")
                        await self.process_last_word_message(original_message, twitch_logger)
                        
                        # Update our last processed time to prevent re-processing
                        self.last_processed_message_time = data['timestamp']
                        
                        # Mark as replied to avoid double responses
                        if message_id in self.message_tracker:
                            self.message_tracker[message_id]['bot_replied'] = True
                            
                    except Exception as e:
                        twitch_logger.error(f"Error processing last word for message {message_id}: {e}")
            elif not candidate_messages:
                twitch_logger.debug("Last word checker found no new unreplied messages to process")
                            
        except Exception as e:
            try:
                from api.twitch_bot import logger as twitch_logger
                twitch_logger.error(f"Error in last word checker: {e}")
            except:
                logger.error(f"Error in last word checker: {e}")

    async def process_last_word_message(self, message, logger):
        """Process a message for the last word feature."""
        logger.info(f"Processing last word for message from {message.author}: {message.content}")
        
        # Generate AI response
        try:
            from api.chat_utils import process_ai_message
            import utils.tokensArray as tokensArray
            
            # Use separate context for last word (to avoid interfering with main conversation)
            last_word_context = []
            
            # Generate AI response 
            def generate_ai_response():
                return process_ai_message(
                    user_message=message.content,
                    conversation_mode="normal", 
                    contextHistory=last_word_context,
                    platform="discord",
                    logger=logger
                )
            
            # Run AI processing in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, generate_ai_response)
            
            if response:
                # Clean and truncate for Discord (2000 char limit)
                from api.chat_utils import clean_text_for_chat
                cleaned_response = clean_text_for_chat(response)
                truncated_response = tokensArray.truncate_to_byte_limit(cleaned_response, 1900)
                
                logger.info(f"Sending last word AI reply to Discord: {truncated_response[:100]}...")
                # Use actual Discord reply instead of regular message
                sent_message = await message.reply(truncated_response)
                logger.info("Successfully sent last word AI reply to Discord")
                
                # Track bot's response message for reply detection (only if last word feature is enabled)
                if getattr(config, 'DISCORD_LAST_WORD_ENABLED', True):
                    self.message_tracker[sent_message.id] = {
                        'timestamp': datetime.now(),
                        'has_replies': False,
                        'content': truncated_response,
                        'author': 'BOT',
                        'bot_replied': True  # Mark as already replied since it's from the bot
                    }
            else:
                logger.warning("No AI response generated for last word message")
                
        except Exception as e:
            logger.error(f"Error in last word AI processing: {e}")
            logger.exception("Last word AI processing exception:")
    
    async def close(self):
        """Clean shutdown of the bot."""
        try:
            from api.twitch_bot import logger as twitch_logger
            twitch_logger.info("Discord bot shutting down - cancelling background tasks...")
            
            # Cancel the message queue processor task if it exists
            if hasattr(self, 'message_queue_task') and self.message_queue_task and not self.message_queue_task.done():
                self.message_queue_task.cancel()
                twitch_logger.info("Cancelled message queue processor task")
            
            # Cancel the last word checker task if it exists to prevent hanging tasks
            if hasattr(self, 'last_word_task') and self.last_word_task and not self.last_word_task.done():
                self.last_word_task.cancel()
                twitch_logger.info("Cancelled last word checker task")
                
        except Exception as e:
            try:
                from api.twitch_bot import logger as twitch_logger
                twitch_logger.error(f"Error during bot shutdown: {e}")
            except:
                logger.error(f"Error during bot shutdown: {e}")
        await super().close()

    async def process_message_queue(self):
        """Process messages from the queue and send them to Discord.
        
        This runs continuously and processes messages that other parts of the bot
        (like the Twitch bot) want to send to Discord via the queue.
        """
        # Use the same logger as the Twitch bot to keep logs in same file
        from api.twitch_bot import logger as twitch_logger
        
        twitch_logger.info("Discord message queue processor started")
        message_count = 0
        failed_count = 0
        
        try:
            while True:
                try:
                    # Check for messages in the queue (non-blocking)
                    if not message_queue.empty():
                        message_text = message_queue.get_nowait()
                        message_count += 1
                        twitch_logger.info(f"Processing Discord message #{message_count}: {message_text[:100]}...")
                        
                        try:
                            await self.send_message_to_discord(message_text)
                            twitch_logger.info(f"Successfully sent message #{message_count} to Discord")
                        except Exception as send_error:
                            failed_count += 1
                            twitch_logger.error(f"Failed to send message #{message_count} to Discord: {send_error}")
                            twitch_logger.info(f"Discord send stats - Success: {message_count - failed_count}, Failed: {failed_count}")
                    
                    # Wait a bit before checking again (prevents busy waiting)
                    await asyncio.sleep(0.1)
                    
                except asyncio.CancelledError:
                    # Task was cancelled (likely due to shutdown) - break gracefully
                    twitch_logger.info("Message queue processor cancelled - shutting down gracefully")
                    raise  # Re-raise to properly handle the cancellation
                    
                except Exception as e:
                    twitch_logger.error(f"Error processing message queue: {e}")
                    twitch_logger.exception("Message queue processing exception:")
                    await asyncio.sleep(1)  # Wait longer on error
                    
        except asyncio.CancelledError:
            # Final cancellation handling - ensure we exit cleanly
            twitch_logger.info(f"Message queue processor task cancelled during shutdown - processed {message_count} messages total")
            # Don't re-raise here - let the task end gracefully

    async def on_message(self, message):
        """Handle Discord messages."""
        try:
            # Use the same logger as the Twitch bot to ensure logs go to the same file
            from api.twitch_bot import logger as twitch_logger
            
            # Don't respond to own messages but track them for reply detection (only if last word feature is enabled)
            if message.author == self.user:
                # Track bot's own messages and mark previous messages as having replies
                if getattr(config, 'DISCORD_LAST_WORD_ENABLED', True):
                    # Mark all previous unreplied messages as having replies (bot activity counts as replies)
                    # This prevents the last word feature from triggering when the bot is actively participating
                    current_time = datetime.now()
                    for msg_id, data in self.message_tracker.items():
                        if not data['has_replies'] and data['timestamp'] < current_time:
                            data['has_replies'] = True
                            twitch_logger.debug(f"Marked message from {data['author']} as having replies due to bot response")
                    
                    # Track this bot message for future reply detection
                    self.message_tracker[message.id] = {
                        'timestamp': current_time,
                        'has_replies': False,
                        'content': message.content,
                        'author': 'BOT',
                        'bot_replied': True  # Mark as already replied since it's from the bot
                    }
                return
                
            # Only respond in the configured channel
            if message.channel.id != self.channel_id:
                return
                
            twitch_logger.info(f"Received Discord message from {message.author}: {message.content}")
            
            # Track message for last word feature (if enabled) - only track user messages, not bot messages
            if getattr(config, 'DISCORD_LAST_WORD_ENABLED', True):
                # Mark all previous unreplied messages as having replies (since someone just posted)
                # This simulates real Discord behavior where people reply by posting new messages, not using formal replies
                current_time = datetime.now()
                for msg_id, data in self.message_tracker.items():
                    if not data['has_replies'] and data['timestamp'] < current_time:
                        data['has_replies'] = True
                        twitch_logger.debug(f"Marked message from {data['author']} as having replies due to new message")
                
                # Add this new message to tracking for future last word processing
                self.message_tracker[message.id] = {
                    'timestamp': current_time,
                    'has_replies': False,
                    'content': message.content,
                    'author': message.author.name,
                    'bot_replied': False
                }
            
            # Check if this is a formal reply to one of our messages (using Discord's reply feature)
            is_reply_to_bot = False
            if message.reference and getattr(config, 'DISCORD_RESPOND_TO_REPLIES', True):
                try:
                    replied_message = await message.channel.fetch_message(message.reference.message_id)
                    if replied_message.author == self.user:
                        is_reply_to_bot = True
                        twitch_logger.info(f"Message is a formal reply to bot - will respond")
                    
                    # Mark the specifically replied message as having replies (this happens in addition to the general logic above)
                    # This handles the less common case where people actually use Discord's reply button
                    if message.reference.message_id in self.message_tracker:
                        self.message_tracker[message.reference.message_id]['has_replies'] = True
                        twitch_logger.debug(f"Marked specifically replied message as having replies")
                except Exception as e:
                    twitch_logger.debug(f"Could not fetch replied message: {e}")
            
            # Check if bot is mentioned
            is_bot_mentioned = False
            if getattr(config, 'DISCORD_RESPOND_TO_MENTIONS', True):
                if self.user in message.mentions:
                    is_bot_mentioned = True
                    twitch_logger.info(f"Bot mentioned in message - will respond")
            
            # Check for special commands FIRST - this prevents double responses
            # Commands like "wiki", "career", "history" always get responses regardless of dice roll
            
            # Clean message content by removing bot mentions for command detection
            clean_content = message.content
            if self.user in message.mentions:
                # Remove the mention from the message content for command parsing
                clean_content = message.content.replace(f'<@{self.user.id}>', '').replace(f'<@!{self.user.id}>', '').strip()
            
            msg_lower = clean_content.lower()
            if self.should_always_respond(msg_lower):
                twitch_logger.info(f"Processing Discord command: {clean_content}")
                # Create a modified message object for command processing with clean content
                original_content = message.content
                message.content = clean_content  # Temporarily modify for command processing
                await self.process_discord_command(message, twitch_logger)
                message.content = original_content  # Restore original content
                return  # Exit early - don't go through dice roll system
            
            # Determine if we should respond
            should_respond = False
            
            # Always respond to mentions and replies (if enabled)
            if is_bot_mentioned or is_reply_to_bot:
                should_respond = True
                twitch_logger.info(f"Responding due to mention/reply - mentioned: {is_bot_mentioned}, reply: {is_reply_to_bot}")
            else:
                # For regular messages (non-commands), use dice roll system with Discord-specific probability
                # Discord gets lower probability than Twitch because Discord channels are typically more active
                import random
                roll = random.random()
                discord_threshold = getattr(config, 'DISCORD_DICE_RESPONSE_PROBABILITY', 0.35)
                
                twitch_logger.debug(f"Discord dice roll: {roll:.2f} vs threshold: {discord_threshold}")
                
                if roll < discord_threshold:
                    should_respond = True
                    twitch_logger.info(f"Discord dice roll passed - will respond")
                else:
                    twitch_logger.debug(f"Discord dice roll failed - will not respond to: {message.content}")
            
            if should_respond:
                await self.process_discord_ai_message(message, twitch_logger)
                
        except Exception as e:
            twitch_logger.error(f"Error processing Discord message: {e}")
            twitch_logger.exception("Discord message processing exception:")
            
        # Process commands (Discord.py built-in command processing)
        await self.process_commands(message)
    
    def should_always_respond(self, msg_lower):
        """Check if message contains commands that should always get a response."""
        return ('open sesame' in msg_lower or 
                any(sub.lower() == msg_lower for sub in getattr(config, 'OPEN_SESAME_SUBSTITUTES', [])) or
                'commands' in msg_lower or
                'wiki' in msg_lower or
                'career' in msg_lower or
                'history' in msg_lower)
    
    async def process_discord_command(self, message, logger):
        """Process Discord commands that should always respond."""
        try:
            msg_lower = message.content.lower()
            
            # Handle commands
            if 'commands' in msg_lower:
                await message.channel.send("Available commands: `wiki <topic>`, `career <player>`, `history <player>`, `open sesame`")
                return
            
            # Handle wiki searches
            if 'wiki' in msg_lower:
                # Extract search query more precisely
                parts = message.content.split()
                wiki_index = next((i for i, part in enumerate(parts) if 'wiki' in part.lower()), None)
                
                if wiki_index is not None and wiki_index + 1 < len(parts):
                    # Get everything after "wiki" as the search query
                    wiki_query = ' '.join(parts[wiki_index + 1:])
                    wiki_query = wiki_query.strip('@').strip()  # Clean up mentions
                    if wiki_query:
                        await self.handle_wiki_search(message, wiki_query, logger)
                    else:
                        await message.channel.send("Usage: `wiki <topic>` - Search for StarCraft 2 information")
                else:
                    await message.channel.send("Usage: `wiki <topic>` - Search for StarCraft 2 information")
                return
                    
            # Handle career searches
            if 'career' in msg_lower:
                # Extract player name more precisely
                parts = message.content.lower().split()
                career_index = next((i for i, part in enumerate(parts) if 'career' in part), None)
                
                if career_index is not None and career_index + 1 < len(parts):
                    # Get the word immediately after "career"
                    player_name = parts[career_index + 1]
                    # Remove any @ mentions or special characters
                    player_name = player_name.strip('@').strip()
                    if player_name:
                        await self.handle_career_search(message, player_name, logger)
                    else:
                        await message.channel.send("Usage: `career <player>` - Look up player career stats")
                else:
                    await message.channel.send("Usage: `career <player>` - Look up player career stats")
                return
            
            # Handle history searches
            if 'history' in msg_lower:
                # Extract player name more precisely, similar to Twitch bot
                parts = message.content.lower().split()
                history_index = next((i for i, part in enumerate(parts) if 'history' in part), None)
                
                if history_index is not None and history_index + 1 < len(parts):
                    # Get the word immediately after "history"
                    player_name = parts[history_index + 1]
                    # Remove any @ mentions or special characters
                    player_name = player_name.strip('@').strip()
                    if player_name:
                        await self.handle_history_search(message, player_name, logger)
                    else:
                        await message.channel.send("Usage: `history <player>` - Look up player game history")
                else:
                    await message.channel.send("Usage: `history <player>` - Look up player game history")
                return
            
            # Handle open sesame and other AI triggers
            await self.process_discord_ai_message(message, logger)
            
        except Exception as e:
            logger.error(f"Error processing Discord command: {e}")
            await message.channel.send("Sorry, I encountered an error processing your command.")
    
    async def handle_wiki_search(self, message, query, logger):
        """Handle wiki searches for Discord."""
        try:
            import utils.wiki_utils as wiki_utils
            # Use the correct function name and signature
            result = wiki_utils.wikipedia_question(query, self)
            
            # Truncate for Discord's 2000 character limit
            if len(result) > 1900:
                result = result[:1900] + "... (truncated)"
                
            await message.channel.send(result)
            logger.info(f"Sent wiki result for '{query}' to Discord")
            
        except Exception as e:
            logger.error(f"Error in Discord wiki search: {e}")
            await message.channel.send("Sorry, I couldn't find that information.")
    
    async def handle_career_search(self, message, query, logger):
        """Handle career searches for Discord."""
        try:
            # Import career search functionality
            import api.aligulac as aligulac
            result = aligulac.get_player_info(query)
            
            # Truncate for Discord's 2000 character limit
            if len(result) > 1900:
                result = result[:1900] + "... (truncated)"
                
            await message.channel.send(result)
            logger.info(f"Sent career result for '{query}' to Discord")
            
        except Exception as e:
            logger.error(f"Error in Discord career search: {e}")
            await message.channel.send("Sorry, I couldn't find that player information.")
    
    async def handle_history_search(self, message, player_name, logger):
        """Handle history searches for Discord."""
        try:
            # Get database connection from twitch bot if available
            db = None
            if self.twitch_bot and hasattr(self.twitch_bot, 'db'):
                db = self.twitch_bot.db
            else:
                # Import and create database connection if needed
                from models.mathison_db import Database
                db = Database()
            
            # Query player records from database
            history_list = db.get_player_records(player_name)
            logger.debug(f"History query for '{player_name}' returned: {str(history_list)}")
            
            if history_list and len(history_list) > 0:
                try:
                    # Validate and format records same as Twitch bot
                    formatted_records = []
                    total_wins = 0
                    total_losses = 0
                    
                    for rec in history_list:
                        parts = rec.split(', ')
                        if len(parts) >= 4:
                            player1 = parts[0]
                            player2 = parts[1] 
                            wins = int(parts[2].split(' ')[0])
                            losses = int(parts[3].split(' ')[0])
                            
                            formatted_records.append(f"{player1} vs {player2}, {wins}-{losses}")
                            total_wins += wins
                            total_losses += losses
                        else:
                            logger.warning(f"Malformed database record: {rec}")
                    
                    if not formatted_records:
                        logger.error("All database records were malformed")
                        await message.channel.send("I have an issue with the database data format. Please try again later.")
                        return
                        
                    result_string = " and ".join(formatted_records)
                    
                    # Create AI prompt with validation - include totals to prevent AI errors
                    ai_prompt = f"restate all of the info here and do not exclude anything: total win/loss record of {player_name} we know the results of so far {result_string}. The total is {total_wins} wins and {total_losses} losses."
                    
                    logger.debug(f"Calculated totals for {player_name}: {total_wins} wins, {total_losses} losses")
                    
                    # Process with AI for natural response
                    await self.process_history_with_ai(message, ai_prompt, logger)
                    logger.info(f"Sent history result for '{player_name}' to Discord")
                    
                except (ValueError, IndexError) as e:
                    logger.error(f"Error parsing database records for '{player_name}': {e}")
                    await message.channel.send("I have an issue parsing the database data. Please try again later.")
            else:
                # No records found - return direct message, don't use AI
                logger.info(f"No history records found for player '{player_name}'")
                await message.channel.send(f"No game records found for player '{player_name}' in the database.")
                
        except Exception as e:
            logger.error(f"Error in Discord history search for '{player_name}': {e}")
            await message.channel.send("I have an issue connecting with the database. Please try again later.")
    
    async def process_history_with_ai(self, message, ai_prompt, logger):
        """Process history data through AI for natural response."""
        try:
            from api.chat_utils import process_ai_message
            import utils.tokensArray as tokensArray
            
            # Use separate context for history commands (cleared each time like Twitch)
            history_context = []
            
            # Generate AI response 
            def generate_ai_response():
                return process_ai_message(
                    user_message=ai_prompt,
                    conversation_mode="normal", 
                    contextHistory=history_context,
                    platform="discord",
                    logger=logger
                )
            
            # Run AI processing in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, generate_ai_response)
            
            if response:
                # Clean and truncate for Discord (2000 char limit)
                from api.chat_utils import clean_text_for_chat
                cleaned_response = clean_text_for_chat(response)
                truncated_response = tokensArray.truncate_to_byte_limit(cleaned_response, 1900)
                
                logger.info(f"Sending history AI response to Discord: {truncated_response[:100]}...")
                await message.channel.send(truncated_response)
                logger.info("Successfully sent history AI response to Discord")
            else:
                logger.warning("No AI response generated for history command")
                await message.channel.send("Sorry, I couldn't generate a response for that history request.")
                
        except Exception as e:
            logger.error(f"Error processing history with AI: {e}")
            await message.channel.send("Sorry, I encountered an error processing the history data.")
    
    async def process_discord_ai_message(self, message, logger):
        """Process Discord message for AI response using clean abstraction."""
        try:
            from api.chat_utils import process_ai_message
            import utils.tokensArray as tokensArray
            
            # Use separate context history for Discord
            if not hasattr(self, 'discord_context_history'):
                self.discord_context_history = []
            
            # Process with the clean AI function in a thread to avoid blocking
            def generate_ai_response():
                return process_ai_message(
                    user_message=message.content,
                    conversation_mode="normal", 
                    contextHistory=self.discord_context_history,
                    platform="discord",
                    logger=logger
                )
            
            # Run AI processing in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, generate_ai_response)
            
            if response:
                # Clean and truncate for Discord (2000 char limit)
                from api.chat_utils import clean_text_for_chat
                cleaned_response = clean_text_for_chat(response)
                truncated_response = tokensArray.truncate_to_byte_limit(cleaned_response, 1900)
                
                logger.info(f"Sending AI response to Discord: {truncated_response[:100]}...")
                sent_message = await message.channel.send(truncated_response)
                logger.info("Successfully sent AI response to Discord")
                
                # Track bot's response message for reply detection (only if last word feature is enabled)
                if getattr(config, 'DISCORD_LAST_WORD_ENABLED', True):
                    self.message_tracker[sent_message.id] = {
                        'timestamp': datetime.now(),
                        'has_replies': False,
                        'content': truncated_response,
                        'author': 'BOT',
                        'bot_replied': True  # Mark as already replied since it's from the bot
                    }
            else:
                logger.warning("No AI response generated for Discord message")
                
        except Exception as e:
            logger.error(f"Error in Discord AI processing: {e}")
            logger.exception("Discord AI processing exception:")
            await message.channel.send("Sorry, I encountered an error processing your message.")

    def process_discord_message_for_ai(self, message, mock_self, msg_lower, twitch_logger):
        """DEPRECATED: Old method - use process_discord_ai_message instead."""
        # This method is deprecated but kept for compatibility during transition
        pass

    async def send_message_to_discord(self, message_text):
        """Send a message to the configured Discord channel."""
        # Use the same logger as the Twitch bot
        from api.twitch_bot import logger as twitch_logger
        
        twitch_logger.debug(f"Attempting to send Discord message: {message_text[:100]}...")
        
        if not self.channel_id:
            twitch_logger.error("No Discord channel ID set")
            return
            
        channel = self.get_channel(self.channel_id)
        if channel:
            try:
                # Clean and truncate message for Discord (2000 char limit)
                cleaned_message = clean_text_for_chat(message_text)
                truncated_message = tokensArray.truncate_to_byte_limit(cleaned_message, 2000)
                
                twitch_logger.info(f"Sending to Discord channel '{channel.name}': {truncated_message}")
                await channel.send(truncated_message)
                twitch_logger.info(f"Successfully sent message to Discord")
            except Exception as e:
                twitch_logger.error(f"Failed to send message to Discord: {e}")
                twitch_logger.exception("Discord send exception:")
        else:
            twitch_logger.error(f"Discord channel not found: {self.channel_id}")

# Global Discord bot instance - allows other modules to access the bot
discord_bot_instance = None

def get_discord_bot():
    """Get the Discord bot instance.
    
    Returns the global Discord bot instance so other parts of the application
    can interact with it (e.g., to check if it's ready, send messages, etc.).
    """
    return discord_bot_instance

def queue_message_for_discord(message_text):
    """Queue a message to be sent to Discord.
    
    This is the main interface used by other parts of the bot (like Twitch bot)
    to send messages to Discord. Messages are queued and processed asynchronously.
    """
    try:
        # Use the same logger as the Twitch bot to keep logs in same file
        from api.twitch_bot import logger as twitch_logger
        
        # Simple connection check - only queue if Discord bot is ready
        # This prevents messages from being lost if Discord is disconnected
        if discord_bot_instance and discord_bot_instance.is_ready():
            message_queue.put_nowait(message_text)
            twitch_logger.info(f"Queued message for Discord (queue size: {message_queue.qsize()}): {message_text[:100]}...")
        else:
            twitch_logger.debug(f"Discord bot not ready - skipping message: {message_text[:100]}...")
    except Exception as e:
        twitch_logger.error(f"Failed to queue Discord message: {e}")
        twitch_logger.exception("Queue message exception:")

async def start_discord_bot(twitch_bot_ref=None):
    """Start the Discord bot."""
    global discord_bot_instance
    
    # Use the same logger as the Twitch bot to ensure logs go to the same file
    from api.twitch_bot import logger as twitch_logger
    
    twitch_logger.info("=== DISCORD BOT STARTUP PROCESS ===")
    twitch_logger.info(f"Discord enabled check: {hasattr(config, 'DISCORD_ENABLED')} - {getattr(config, 'DISCORD_ENABLED', 'NOT_SET')}")
    twitch_logger.info(f"Discord token check: {hasattr(config, 'DISCORD_TOKEN')} - {'SET' if getattr(config, 'DISCORD_TOKEN', '') else 'EMPTY'}")
    twitch_logger.info(f"Discord channel ID check: {hasattr(config, 'DISCORD_CHANNEL_ID')} - {getattr(config, 'DISCORD_CHANNEL_ID', 'NOT_SET')}")
    
    if not hasattr(config, 'DISCORD_TOKEN') or not config.DISCORD_TOKEN:
        twitch_logger.warning("Discord bot disabled - no token provided")
        return None
        
    if not hasattr(config, 'DISCORD_CHANNEL_ID') or not config.DISCORD_CHANNEL_ID:
        twitch_logger.warning("Discord bot disabled - no channel ID provided")
        return None
    
    try:
        twitch_logger.info("Creating Discord bot instance...")
        discord_bot_instance = DiscordBot(twitch_bot_ref)
        twitch_logger.info("Discord bot instance created, attempting to start...")
        await discord_bot_instance.start(config.DISCORD_TOKEN)
        twitch_logger.info("Discord bot started successfully!")
    except Exception as e:
        twitch_logger.error(f"Failed to start Discord bot: {e}")
        twitch_logger.exception("Discord bot startup exception details:")
        return None
    
    return discord_bot_instance 