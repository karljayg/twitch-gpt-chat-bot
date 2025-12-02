import random
import pygame
import logging
import json

from settings import config

#logger = logging.getLogger(__name__)


class SoundPlayer:
    def __init__(self):
        self.audio_available = False
        self.sounds_config = {}
        
        # Try to initialize pygame mixer
        try:
            pygame.mixer.init()
            pygame.mixer.music.set_volume(0.7)
            self.audio_available = True
            
            # Load SC2 sounds config
            try:
                with open(config.SOUNDS_CONFIG_FILE) as f:
                    self.sounds_config = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Warning: Could not load sounds config: {e}")
                self.sounds_config = {'sounds': {}}
                
        except Exception as pygame_error:
            # This catches pygame.error and other pygame-related exceptions
            if "dsp" in str(pygame_error) or "audio" in str(pygame_error).lower():
                print(f"Warning: Audio device not available, sounds will be disabled: {pygame_error}")
            else:
                print(f"Warning: Pygame initialization failed: {pygame_error}")
            self.audio_available = False
        except Exception as e:
            print(f"Warning: Unexpected error initializing audio: {e}")
            self.audio_available = False

    def play_sound(self, game_event, logger):
        # Check if audio is available
        if not self.audio_available:
            logger.warning(f"Audio not available - would have played: {game_event}")
            return
            
        try:
            if game_event in self.sounds_config.get('sounds', {}): 
                sound_file = random.choice(
                    self.sounds_config['sounds'][game_event])
                
                # Check if file exists before trying to load
                import os
                if not os.path.exists(sound_file):
                    logger.error(f"Sound file not found: {sound_file}")
                    return
                
                logger.info(f"SoundPlayer: Loading sound file: {sound_file}")
                pygame.mixer.music.load(sound_file)
                pygame.mixer.music.play()
                logger.info(f"SoundPlayer: Playing sound '{game_event}' from file: {sound_file}")
            else:
                logger.warning(f"Sound for game event '{game_event}' not found in config.")
        except Exception as e:
            logger.error(f"An error occurred while trying to play sound '{game_event}': {e}", exc_info=True)
