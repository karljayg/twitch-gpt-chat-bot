import logging
import asyncio
from typing import Optional
from core.interfaces import IChatService
from core.bot import BotCore
from core.events import MessageEvent
from utils import tokensArray

logger = logging.getLogger(__name__)

class TwitchAdapter(IChatService):
    def __init__(self, bot_core: BotCore, twitch_bot_instance=None):
        """
        :param bot_core: The core logic where we send events.
        :param twitch_bot_instance: The legacy TwitchBot instance (if we reuse it).
        """
        self.bot_core = bot_core
        self.twitch_bot = twitch_bot_instance
        self.platform = "twitch"
        
        # Capture the main loop for thread-safe dispatch
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.get_event_loop()

    def get_platform_name(self) -> str:
        return self.platform

    async def send_message(self, channel: str, message: str) -> None:
        """
        Forwards the send request to the actual TwitchBot instance.
        """
        if self.twitch_bot and hasattr(self.twitch_bot, 'connection'):
            try:
                # The legacy bot uses synchronous privmsg, but this method is async.
                # In a full asyncio rewrite, we'd use twitchio. 
                # For now, we wrap the sync call.
                
                # Handle generic channel names by using the bot's configured channel
                target_channel = channel
                if channel == "channel" and hasattr(self.twitch_bot, 'channel'):
                    target_channel = self.twitch_bot.channel
                    
                self.twitch_bot.connection.privmsg(target_channel, message)
                # Sanitize for logging (remove non-ASCII characters that can't be encoded in console)
                safe_message = tokensArray.replace_non_ascii(message, replacement='?')
                logger.info(f"Sent to Twitch: {safe_message}")
            except Exception as e:
                logger.error(f"Failed to send message to Twitch: {e}")
        else:
            logger.warning("TwitchBot instance not connected or unavailable.")

    def on_message(self, author: str, content: str, channel: str):
        """
        Callback that the legacy TwitchBot should call when it receives a message.
        This is called from the TwitchBot thread, so we must be thread-safe.
        """
        event = MessageEvent(
            platform=self.platform,
            author=author,
            content=content,
            channel=channel
        )
        
        # Dispatch to main loop thread-safely
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.bot_core.add_event, event)
        else:
            logger.warning("Main loop not available, attempting direct add (unsafe)")
            self.bot_core.add_event(event)
