import asyncio
import logging
from typing import Any, Optional
from core.interfaces import IAudioService

logger = logging.getLogger(__name__)

class AudioService(IAudioService):
    """
    Service for handling Audio Output (TTS and SFX).
    Wraps legacy api.text2speech and utils.sound_player_utils.
    """
    def __init__(self, sound_player: Any = None, tts_module: Any = None):
        self.sound_player = sound_player
        self.tts_module = tts_module
        
    async def speak(self, text: str) -> None:
        if not self.tts_module:
            logger.warning("TTS module not provided or disabled.")
            return
            
        loop = asyncio.get_running_loop()
        try:
            # speak_text(text, mode=1) is the legacy signature
            await loop.run_in_executor(None, self.tts_module.speak_text, text)
        except Exception as e:
            logger.error(f"Error in TTS: {e}")

    async def play_sound(self, sound_key: str) -> None:
        if not self.sound_player:
            logger.debug("Sound player not provided or disabled.")
            return
            
        loop = asyncio.get_running_loop()
        try:
            # Legacy play_sound takes (game_event, logger)
            await loop.run_in_executor(None, self.sound_player.play_sound, sound_key, logger)
        except Exception as e:
            logger.error(f"Error playing sound: {e}")


