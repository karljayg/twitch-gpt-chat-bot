import logging
import asyncio
import requests
from typing import Optional
from core.interfaces import IChatService
from core.bot import BotCore
from core.events import MessageEvent
from utils import tokensArray
import settings.config as config

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
    
    async def send_whisper(self, username: str, message: str) -> None:
        """
        Sends a whisper (private message) to a Twitch user using Twitch API.
        IRC whispers were deprecated in Feb 2023, must use API now.
        Requires OAuth token with 'user:manage:whispers' scope.
        """
        try:
            # Get bot's user ID first
            bot_user_id = None
            headers = {
                "Client-ID": config.CLIENT_ID,
                "Authorization": f"Bearer {config.TOKEN}"
            }
            
            # Get bot's own user ID
            response = requests.get("https://api.twitch.tv/helix/users", headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data.get('data') and len(data['data']) > 0:
                    bot_user_id = data['data'][0]['id']
                else:
                    logger.error("Could not get bot user ID from Twitch API")
                    return
            else:
                logger.error(f"Failed to get bot user ID: {response.status_code} - {response.text}")
                return
            
            # Get target user's ID
            target_user_id = None
            response = requests.get(
                f"https://api.twitch.tv/helix/users?login={username}",
                headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('data') and len(data['data']) > 0:
                    target_user_id = data['data'][0]['id']
                else:
                    logger.error(f"User {username} not found")
                    return
            else:
                logger.error(f"Failed to get user ID for {username}: {response.status_code} - {response.text}")
                return
            
            # Send whisper via API
            whisper_url = "https://api.twitch.tv/helix/whispers"
            whisper_headers = {
                "Client-ID": config.CLIENT_ID,
                "Authorization": f"Bearer {config.TOKEN}",
                "Content-Type": "application/json"
            }
            whisper_data = {
                "from_user_id": bot_user_id,
                "to_user_id": target_user_id,
                "message": message
            }
            
            response = requests.post(whisper_url, headers=whisper_headers, json=whisper_data)
            if response.status_code in [200, 204]:
                safe_message = tokensArray.replace_non_ascii(message, replacement='?')
                logger.info(f"Sent whisper to {username} via API: {safe_message}")
            else:
                logger.error(f"Failed to send whisper to {username}: {response.status_code} - {response.text}")
                # Fallback to public message if whisper fails
                logger.warning(f"Falling back to public message for {username}")
                await self.send_message("channel", f"FSL Review Link for {username}: {message}")
        except Exception as e:
            logger.error(f"Error sending whisper to {username}: {e}")
            logger.exception("Whisper exception details:")
            # Fallback to public message
            try:
                await self.send_message("channel", f"FSL Review Link for {username}: {message}")
            except:
                pass

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
