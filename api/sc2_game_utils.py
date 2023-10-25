import json
import requests
import logging


from settings import config
from models.game_info import GameInfo

logger = logging.getLogger(__name__)


@staticmethod
def check_SC2_game_status():
    if config.TEST_MODE_SC2_CLIENT_JSON:
        try:
            with open(config.GAME_RESULT_TEST_FILE, 'r') as file:
                json_data = json.load(file)
            return GameInfo(json_data)
        except Exception as e:
            logger.debug(
                f"An error occurred while reading the test file: {e}")
            return None
    else:
        try:
            response = requests.get("http://localhost:6119/game")
            response.raise_for_status()
            return GameInfo(response.json())
        except Exception as e:
            logger.debug(f"Is SC2 on? error: {e}")
            return None
