import random
import pygame
import logging
import json

from settings import config

logger = logging.getLogger(__name__)


class SoundPlayer:
    def __init__(self):
        pygame.mixer.init()
        pygame.mixer.music.set_volume(0.7)
        # SC2 sounds
        with open(config.SOUNDS_CONFIG_FILE) as f:
            self.sounds_config = json.load(f)

    def play_sound(self, game_event):
        try:
            if game_event in self.sounds_config['sounds']:
                sound_file = random.choice(
                    self.sounds_config['sounds'][game_event])
                pygame.mixer.music.load(sound_file)
                pygame.mixer.music.play()
                logger.debug(f"Playing sound: {game_event}")
            else:
                logger.debu(f"Sound for game event '{game_event}' not found.")
        except Exception as e:
            logger.debu(f"An error occurred while trying to play sound: {e}")
