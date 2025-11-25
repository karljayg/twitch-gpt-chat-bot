import logging
import discord
from core.interfaces import IChatService
from core.bot import BotCore
from core.events import MessageEvent

logger = logging.getLogger(__name__)

class DiscordAdapter(IChatService):
    def __init__(self, bot_core: BotCore, discord_bot_instance=None):
        """
        :param bot_core: The core logic where we send events.
        :param discord_bot_instance: The DiscordBot instance.
        """
        self.bot_core = bot_core
        self.discord_bot = discord_bot_instance
        self.platform = "discord"
        
        # If bot instance is provided, register the message listener immediately
        if self.discord_bot:
            self._register_listener()

    def set_discord_bot(self, discord_bot_instance):
        """Setter for discord bot instance if not available at init"""
        self.discord_bot = discord_bot_instance
        self._register_listener()

    def _register_listener(self):
        """Registers the on_message listener with the discord bot"""
        if self.discord_bot:
            # Remove existing listener if any to avoid duplicates
            if hasattr(self, '_handle_discord_message'):
                self.discord_bot.remove_listener(self._handle_discord_message, 'on_message')
            
            self.discord_bot.add_listener(self._handle_discord_message, 'on_message')
            logger.info("Registered DiscordAdapter message listener")

    async def _handle_discord_message(self, message):
        """
        Internal listener that receives raw discord.Message objects
        and converts them to Core MessageEvents.
        """
        # Ignore own messages
        if message.author == self.discord_bot.user:
            return

        # Only process messages from the configured channel
        # If channel_id is not set (not ready or not configured), ignore messages
        if not hasattr(self.discord_bot, 'channel_id') or not self.discord_bot.channel_id:
            return
            
        if message.channel.id != self.discord_bot.channel_id:
            return
        
        # Create and push event
        # We use message.channel.id as the channel identifier
        self.on_message(
            author=message.author.name,
            content=message.content,
            channel=str(message.channel.id), # Use ID for consistency
            platform=self.platform # Explicitly pass platform
        )

    def get_platform_name(self) -> str:
        return self.platform

    async def send_message(self, channel: str, message: str) -> None:
        """
        Forwards the send request to the DiscordBot instance.
        :param channel: Can be a channel ID (str/int) or name. 
                        For simplicity, we assume it's an ID or the bot knows the default channel.
        """
        if self.discord_bot:
            try:
                # If the channel argument is a generic name, use the default Discord channel
                if str(channel).lower() in ["discord", "chat", "channel", "general"] or str(channel) == str(getattr(self.discord_bot, 'channel_id', '')):
                    await self.discord_bot.send_message_to_discord(message)
                    return
                
                # Try to find the channel object by ID
                try:
                    channel_id = int(channel)
                    discord_channel = self.discord_bot.get_channel(channel_id)
                    if discord_channel:
                        await discord_channel.send(message)
                    else:
                        logger.error(f"Discord channel {channel} not found.")
                except ValueError:
                    # If not an int ID, log warning (or could try name lookup)
                    logger.error(f"Invalid Discord channel ID format: {channel}")
            except Exception as e:
                logger.error(f"Failed to send message to Discord: {e}")
        else:
            logger.warning("DiscordBot instance not available.")

    def on_message(self, author: str, content: str, channel: str, platform: str = "discord"):
        """
        Callback to push Discord messages to BotCore.
        """
        event = MessageEvent(
            platform=platform,
            author=author,
            content=content,
            channel=channel
        )
        self.bot_core.add_event(event)
