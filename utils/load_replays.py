from datetime import datetime
from collections import defaultdict
import os
import logging
import json
import spawningtool.parser
import time
import pytz
import sys

# Add the parent directory (project_root) to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from settings import config
from models.mathison_db import Database
from datetime import datetime
# Date range input
start_date, end_date = input('Enter the date range (YYYY-MM-DD to YYYY-MM-DD): ').split(' to ')
start_date = datetime.strptime(start_date.strip(), '%Y-%m-%d')
end_date = datetime.strptime(end_date.strip(), '%Y-%m-%d')
print(f'Date Range: {start_date} to {end_date}')

# Debug mode input
debug_mode = input('Run in debug mode? (yes/no): ').strip().lower() == 'yes'
if debug_mode:
    print('Debug mode activated.')

# Prompt for folder path or username-based substitution
default_path = r"C:\Users\karl_\OneDrive\Documents\StarCraft II\Accounts"
folder_input = input(f"Enter the full path (e.g., {default_path}) "
                     f"OR enter your Windows username (with optional subfolder, e.g., jsmith\\OneDrive) "
                     f"OR press Enter to use default ({default_path}): ").strip()

# Use default path if nothing entered
if not folder_input:
    folder_path = default_path
    print(f"Using default path: {folder_path}")
# Determine if the input is a full path based on the presence of a drive letter (e.g., "C:")
elif ":" in folder_input and "\\" in folder_input:
    folder_path = folder_input
else:
    # If no drive letter is detected, treat input as username/subfolder and use the default structure
    folder_path = fr"C:\Users\{folder_input}\Documents\StarCraft II\Accounts"

# Print out the gathered inputs
print(f"Folder path: {folder_path}\n")    
print(f"Start date: {start_date}\n")  
print(f"End date: {end_date}\n")
print(f"Debug mode: {debug_mode}\n")
input("Press Enter to begin")


class ReplayLoader:

    def find_replay_files(self, folder_path):
        logging.debug(f"Searching in folder: {folder_path}")

        files_count = 0
        files_processed = 0

        # date range to process
        # Removed hardcoded dates as user input is now used

        for root, dirs, files in os.walk(folder_path):

            for folder in dirs:
                folder_location = os.path.join(root, folder)
                self.logger.debug(f"Checking subfolder: {folder_location}")
                # Convert both paths to use forward slashes for the replacement
                folder_location_forward = folder_location.replace("\\", "/")
                replays_folder_forward = folder_path.replace(
                    "\\", "/")

                cleaned_path = folder_location_forward.replace(
                    replays_folder_forward, '')
                self.logger.debug(f"Checking subfolder: {cleaned_path}")

            #testing DB calls here, delete this later
            #self.logger.debug("here ya go:\n" + '\n'.join(self.db.get_player_records('DAYGAMER')))
            #if debug_mode: input("Press Enter to continue...")

            for filename in files:
                if filename.endswith(".SC2Replay"):
                    file_location = os.path.join(root, filename)
                    file_mod_time = os.path.getmtime(file_location)
                    file_date = datetime.fromtimestamp(file_mod_time)  # Convert to datetime

                    # Check if the file modification date is within the range
                    if start_date <= file_date <= end_date:
                        formatted_timestamp = self.db.convertUnixToDatetime(file_mod_time)
                        logging.debug(
                            f"{files_count}/{files_processed} - Found this file: {filename} \n dated: {formatted_timestamp}")
                        # debug mode here, make it stop on each insert attempt
                        if debug_mode: input("Press Enter to continue...")
                        files_count += 1
                        if self.processReplayFile(file_location):
                            files_processed += 1
                self.logger.debug(
                    f"---------------Files found: {files_count}, Files processed: {files_processed}------------")

    def processReplayFile(self, currentFile):
        result = currentFile
        response = ""
        replay_summary = ""  # Initialize summary string

        try:
            replay_data = spawningtool.parser.parse_replay(result)
            replay_summary = ""

            winning_players = []
            losing_players = []

            for player_key, player_data in replay_data['players'].items():
                if player_data['is_winner']:
                    winning_players.append(player_data['name'])
                else:
                    losing_players.append(player_data['name'])

            # Assuming a 1v1 match, this would give you:
            winner = winning_players[0] if winning_players else None
            loser = losing_players[0] if losing_players else None

            # Save the replay JSON to a file
            filename = config.LAST_REPLAY_JSON_FILE
            with open(filename, 'w') as file:
                json.dump(replay_data, file, indent=4)

            # First, create a mapping of player names to their display names (with alias replacement)
            player_display_names = {}
            for player_key, player_data in replay_data['players'].items():
                player_name = player_data['name']
                # Check if this is a streamer alias and replace with nickname
                if any(player_name.lower() == alias.lower() for alias in config.SC2_PLAYER_ACCOUNTS):
                    player_display_names[player_key] = config.STREAMER_NICKNAME
                else:
                    player_display_names[player_key] = player_name

            # Players and Map (using display names with alias replacement)
            players = [f"{player_display_names[player_key]}: {player_data['race']}" for player_key, player_data in
                       replay_data['players'].items()]
            region = replay_data['region']
            game_type = replay_data['game_type']

            if game_type != "1v1":
                return  # we only process 1v1 games

            unix_timestamp = replay_data['unix_timestamp']

            replay_summary += f"Players: {', '.join(players)}\n"
            replay_summary += f"Map: {replay_data['map']}\n"
            replay_summary += f"Region: {region}\n"
            replay_summary += f"Game Type: {game_type}\n"
            replay_summary += f"Timestamp: {unix_timestamp}\n"
            replay_summary += f"Winners: {winner}\n"
            replay_summary += f"Losers: {loser}\n"

            # Game Duration
            frames = replay_data['frames']
            frames_per_second = replay_data['frames_per_second']

            total_seconds = frames / frames_per_second
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)

            game_duration = f"{minutes}m {seconds}s"
            replay_summary += f"Game Duration: {game_duration}\n\n"

            build_order_count = config.BUILD_ORDER_COUNT_TO_ANALYZE

            # Units Lost
            units_lost_summary = {player_key: player_data['unitsLost'] for player_key, player_data in
                                  replay_data['players'].items()}
            for player_key, units_lost in units_lost_summary.items():
                # Use the display name (with alias replacement) instead of raw player name
                display_name = player_display_names[player_key]
                player_info = f"Units Lost by {display_name}"
                replay_summary += player_info + '\n'
                units_lost_aggregate = defaultdict(int)
                if units_lost:  # Check if units_lost is not empty
                    for unit in units_lost:
                        name = unit.get('name', "N/A")
                        units_lost_aggregate[name] += 1
                    for unit_name, count in units_lost_aggregate.items():
                        unit_info = f"{unit_name}: {count}"
                        replay_summary += unit_info + '\n'
                else:
                    replay_summary += "None \n"
                replay_summary += '\n'

            # Build Orders
            build_orders = {player_key: player_data['buildOrder'] for player_key, player_data in
                            replay_data['players'].items()}
            for player_key, build_order in build_orders.items():
                # Use the display name (with alias replacement) instead of raw player name
                display_name = player_display_names[player_key]
                player_info = f"{display_name}'s Build Order (first set of steps):"
                replay_summary += player_info + '\n'
                for order in build_order[:int(build_order_count)]:
                    time = order['time']
                    name = order['name']
                    supply = order['supply']
                    order_info = f"Time: {time}, Name: {name}, Supply: {supply}"
                    replay_summary += order_info + '\n'
                replay_summary += '\n'

            # replace player names with streamer name (case-insensitive)
            import re
            for player_name in config.SC2_PLAYER_ACCOUNTS:
                # Use regex for case-insensitive replacement
                pattern = re.compile(re.escape(player_name), re.IGNORECASE)
                replay_summary = pattern.sub(config.STREAMER_NICKNAME, replay_summary)

            # Save the replay summary to a file
            filename = config.LAST_REPLAY_SUMMARY_FILE
            with open(filename, 'w') as file:
                file.write(replay_summary)
        except Exception as e:
            self.logger.debug(f"error parsing replay: {e}")
            return False

        # Save to the database
        try:
            self.db.insert_replay_info(replay_summary)
            self.logger.debug("replay summary saved to database")
            return True
        except Exception as e:
            self.logger.debug(f"error with database: {e}")

    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger("replay_loader")
        # Generate the current datetime timestamp in the format YYYYMMDD-HHMMSS

        # get timestamp now
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        formatter = logging.Formatter(
            '%(asctime)s:%(levelname)s:%(name)s: %(message)s')
        log_file_name = f"logs/replay_loader_{timestamp}.log"
        file_handler = logging.FileHandler(log_file_name)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.db = Database()
        self.find_replay_files(folder_path)


if __name__ == "__main__":
    loader = ReplayLoader()
