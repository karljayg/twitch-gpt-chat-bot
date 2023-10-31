import logging
import spawningtool.parser
import json
from collections import defaultdict


from settings import config
from utils.file_utils import find_latest_file


logger = logging.getLogger(__name__)


def save_replay_json(replay_data):
    filename = config.LAST_REPLAY_JSON_FILE
    try:
        with open(filename, 'w') as file:
            json.dump(replay_data, file, indent=4)
            logger.debug('Last replay file saved: ' + filename)
    except FileNotFoundError:
        logger.debug(f'The last replay file was not saved. {filename} file does not exist.')

def calculate_game_duration(replay_data):
    res = {}
    frames = replay_data['frames']
    frames_per_second = replay_data['frames_per_second']
    total_seconds = frames / frames_per_second
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    res["totalSeconds"] = total_seconds
    game_duration = f"{minutes}m {seconds}s"
    res["gameDuration"] = game_duration
    logger.debug(f"Game Duration: {game_duration}")    
    return res