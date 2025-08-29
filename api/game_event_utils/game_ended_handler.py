import json
from collections import defaultdict
from datetime import datetime

from settings import config


# This function save file to either json or summary txt file 
def save_file(replay_data, file_type, logger):
    if file_type == 'json':
        filename = config.LAST_REPLAY_JSON_FILE
        try:
            with open(filename, 'w') as file:
                json.dump(replay_data, file, indent=4)
        except FileNotFoundError:
            logger.debug(f'The last replay file was not saved. {filename} file does not exist.')
            return
    elif file_type == 'summary':
        filename = config.LAST_REPLAY_SUMMARY_FILE
        try:
            with open(filename, 'w') as file:
                file.write(replay_data)
        except FileNotFoundError:
            logger.debug(f'The last replay file was not saved. {filename} file does not exist.')
            return
    logger.debug('Last replay file saved: ' + filename)

# This function calculates the game duration
def calculate_game_duration(replay_data, logger):
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

#This function is called if the game is ends. This will analyze and log the game results.
def game_ended(self, game_player_names,winning_players,losing_players, logger):
    if len(winning_players) == 0:
        response = f"Game with {game_player_names} ended with a Tie!"
        self.play_SC2_sound("tie")

    else:
        # Compare with the threshold
        if self.total_seconds < config.ABANDONED_GAME_THRESHOLD:
            logger.debug("Game duration is less than " + str(config.ABANDONED_GAME_THRESHOLD) + " seconds.")
            response = f"The game was abandoned immediately in just {self.total_seconds} seconds between {game_player_names} and so {winning_players} get the free win."
            self.play_SC2_sound("abandoned")  
        else:
            response = f"Game with {game_player_names} ended with {winning_players} beating {losing_players}"
            if config.STREAMER_NICKNAME in winning_players:
                self.play_SC2_sound("victory")
            else:
                self.play_SC2_sound("defeat")
    
        # Check if this is an FSL game and ask for reviewer request

    # Pattern learning system is now triggered after replay is saved to database
    # This ensures we have all the replay data available for analysis
    
    return response

