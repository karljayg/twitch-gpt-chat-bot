import discord
from discord.ext import commands
import logging
import asyncio
import queue
import threading
from settings import config
from api.chat_utils import clean_text_for_chat
import utils.tokensArray as tokensArray

logger = logging.getLogger(__name__)

# Global message queue for sending messages to Discord
message_queue = queue.Queue()

class DiscordBot(commands.Bot):
    def __init__(self, twitch_bot_ref=None):
        intents = discord.Intents.default()
        # Enable message content intent to read Discord messages
        intents.message_content = True
        
        super().__init__(command_prefix='!', intents=intents)
        
        self.twitch_bot = twitch_bot_ref
        self.channel_id = None
        
        # We'll use the same context history as the Twitch bot
        self.contextHistory = []
        if twitch_bot_ref:
            self.contextHistory = twitch_bot_ref.contextHistory if hasattr(twitch_bot_ref, 'contextHistory') else []

    async def on_ready(self):
        """Called when the bot is ready."""
        # Use the same logger as the Twitch bot
        from api.twitch_bot import logger as twitch_logger
        
        twitch_logger.info(f'=== DISCORD BOT CONNECTED ===')
        twitch_logger.info(f'Bot user: {self.user}')
        twitch_logger.info(f'Bot ID: {self.user.id}')
        twitch_logger.info(f'Connected to {len(self.guilds)} guilds')
        
        # Set the channel to monitor
        if config.DISCORD_CHANNEL_ID:
            self.channel_id = config.DISCORD_CHANNEL_ID
            twitch_logger.info(f'Looking for channel ID: {self.channel_id}')
            channel = self.get_channel(self.channel_id)
            if channel:
                twitch_logger.info(f'Found Discord channel: {channel.name} in guild: {channel.guild.name}')
                # Send the same random emoji greeting as Twitch bot
                from utils.emote_utils import get_random_emote
                greeting_message = get_random_emote()
                try:
                    await channel.send(greeting_message)
                    twitch_logger.info(f'Sent greeting message to Discord channel')
                except Exception as e:
                    twitch_logger.error(f'Failed to send greeting message: {e}')
                
                # Start the message processing task
                twitch_logger.info('Starting message queue processor...')
                self.loop.create_task(self.process_message_queue())
            else:
                twitch_logger.error(f'Could not find Discord channel with ID: {self.channel_id}')
                twitch_logger.info('Available channels:')
                for guild in self.guilds:
                    twitch_logger.info(f'  Guild: {guild.name}')
                    for ch in guild.channels:
                        twitch_logger.info(f'    Channel: {ch.name} (ID: {ch.id}) Type: {type(ch)}')
        else:
            twitch_logger.error("No Discord channel ID configured")

    async def process_message_queue(self):
        """Process messages from the queue and send them to Discord."""
        # Use the same logger as the Twitch bot
        from api.twitch_bot import logger as twitch_logger
        
        twitch_logger.info("Discord message queue processor started")
        message_count = 0
        failed_count = 0
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
                
                # Wait a bit before checking again
                await asyncio.sleep(0.1)
            except Exception as e:
                twitch_logger.error(f"Error processing message queue: {e}")
                twitch_logger.exception("Message queue processing exception:")
                await asyncio.sleep(1)

    async def on_message(self, message):
        """Handle Discord messages."""
        try:
            # Use the same logger as the Twitch bot to ensure logs go to the same file
            from api.twitch_bot import logger as twitch_logger
            
            # Don't respond to own messages
            if message.author == self.user:
                return
                
            # Only respond in the configured channel
            if message.channel.id != self.channel_id:
                return
                
            twitch_logger.info(f"Received Discord message from {message.author}: {message.content}")
            
            # Check for special commands FIRST - this prevents double responses
            msg_lower = message.content.lower()
            if self.should_always_respond(msg_lower):
                twitch_logger.info(f"Processing Discord command: {message.content}")
                await self.process_discord_command(message, twitch_logger)
                return  # Exit early - don't go through dice roll system
            
            # For regular messages (non-commands), use dice roll system like Twitch
            import random
            roll = random.random()
            response_threshold = getattr(config, 'RESPONSE_THRESHOLD', 0.7)
            
            twitch_logger.debug(f"Discord dice roll: {roll:.2f} vs threshold: {response_threshold}")
            
            if roll < response_threshold:
                twitch_logger.info(f"Processing Discord message for AI response: {message.content}")
                await self.process_discord_ai_message(message, twitch_logger)
            else:
                twitch_logger.debug(f"Discord dice roll failed - will not respond to: {message.content}")
                
        except Exception as e:
            twitch_logger.error(f"Error processing Discord message: {e}")
            twitch_logger.exception("Discord message processing exception:")
            
        # Process commands
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
                wiki_query = message.content.replace('wiki', '').strip()
                if wiki_query:
                    await self.handle_wiki_search(message, wiki_query, logger)
                else:
                    await message.channel.send("Usage: `wiki <topic>` - Search for StarCraft 2 information")
                return
                    
            # Handle career searches
            if 'career' in msg_lower:
                career_query = message.content.replace('career', '').strip()
                if career_query:
                    await self.handle_career_search(message, career_query, logger)
                else:
                    await message.channel.send("Usage: `career <player>` - Look up player career stats")
                return
            
            # Handle history searches
            if 'history' in msg_lower:
                history_query = message.content.replace('history', '').strip()
                if history_query:
                    await self.handle_history_search(message, history_query, logger)
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
            logger.debug(f"History answer for {player_name}: {str(history_list)}")
            
            if history_list:
                # Format records same as Twitch bot
                formatted_records = [f"{rec.split(', ')[0]} vs {rec.split(', ')[1]}, {rec.split(', ')[2].split(' ')[0]}-{rec.split(', ')[3].split(' ')[0]}" for rec in history_list]
                result_string = " and ".join(formatted_records)
                
                # Create AI prompt similar to Twitch bot
                ai_prompt = f"restate all of the info here and do not exclude anything: total win/loss record of {player_name} we know the results of so far {result_string}"
                
                # Process with AI for natural response
                await self.process_history_with_ai(message, ai_prompt, logger)
            else:
                # No records found
                ai_prompt = f"restate all of the info here: there are no game records in history for {player_name}"
                await self.process_history_with_ai(message, ai_prompt, logger)
                
            logger.info(f"Sent history result for '{player_name}' to Discord")
            
        except Exception as e:
            logger.error(f"Error in Discord history search: {e}")
            await message.channel.send(f"Sorry, I couldn't find history for player '{player_name}'.")
    
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
                await message.channel.send(truncated_response)
                logger.info("Successfully sent AI response to Discord")
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

# Global Discord bot instance
discord_bot_instance = None

def get_discord_bot():
    """Get the Discord bot instance."""
    return discord_bot_instance

def queue_message_for_discord(message_text):
    """Queue a message to be sent to Discord."""
    try:
        # Use the same logger as the Twitch bot
        from api.twitch_bot import logger as twitch_logger
        
        # Simple connection check - only queue if Discord bot is ready
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