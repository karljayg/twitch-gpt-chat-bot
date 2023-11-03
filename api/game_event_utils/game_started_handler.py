import datetime
import logging
import pytz
from ..chat_utils import processMessageForOpenAI

from settings import config

logger = logging.getLogger(__name__)


def game_started(self, current_game, contextHistory):
    # prevent the array brackets from being included
    game_player_names = ', '.join(current_game.get_player_names())
    try:
        # if game_type == "1v1":
        if current_game.total_players == 2:
            logger.debug(
                "1v1 game, so checking if player exists in database")
            game_player_names = [name.strip()
                                    for name in game_player_names.split(',')]
            for player_name in game_player_names:
                logger.debug(f"looking for: {player_name}")
                if player_name != config.STREAMER_NICKNAME:
                    result = self.db.check_player_exists(
                        player_name, current_game.get_player_race(player_name))
                    if result is not None:

                        # Set the timezone for Eastern Time
                        eastern = pytz.timezone('US/Eastern')

                        # already in Eastern Time since it is using DB replay table Date_Played column
                        date_obj = eastern.localize(
                            result['Date_Played'])

                        # Get the current datetime in Eastern Time
                        current_time_eastern = datetime.now(eastern)

                        # Calculate the difference
                        delta = current_time_eastern - date_obj

                        # Extract the number of days
                        days_ago = delta.days
                        hours_ago = delta.seconds // 3600
                        seconds_ago = delta.seconds

                        # Determine the appropriate message
                        if days_ago == 0:
                            mins_ago = seconds_ago // 60
                            if mins_ago > 60:
                                how_long_ago = f"{hours_ago} hours ago."
                            else:
                                how_long_ago = f"{mins_ago} seconds ago."
                        else:
                            how_long_ago = f"{days_ago} days ago"

                        first_30_build_steps = self.db.extract_opponent_build_order(
                            player_name)

                        msg = "Do both: \n"
                        msg += f"Mention all details here: {config.STREAMER_NICKNAME} played {player_name} {how_long_ago} in {{Map name}},"
                        msg += f"and the result was a {{Win/Loss for {config.STREAMER_NICKNAME}}} in {{game duration}}. \n"
                        msg += f"As a StarCraft 2 expert, comment on last game summary. Be concise with only 2 sentences total of 25 words or less. \n"
                        msg += "-----\n"
                        msg += f"last game summary: \n {result['Replay_Summary']} \n"
                        processMessageForOpenAI(self, msg,  "last_time_played", logger, contextHistory)
                        #self.processMessageForOpenAI(
                        #   msg, "last_time_played")

                        msg = f"Do both: \n"
                        msg += "First, print the build order exactly as shown. \n"
                        msg += "After, summarize the build order 7 words or less. \n"
                        msg += "-----\n"
                        msg += f"{first_30_build_steps} \n"
                        processMessageForOpenAI(self, msg,  "last_time_played", logger, contextHistory)
                        #self.processMessageForOpenAI(
                        #    msg, "last_time_played")

                    else:
                        msg = "Restate this without missing any details: \n "
                        msg += f"I think this is the first time {config.STREAMER_NICKNAME} is playing {player_name}, at least the {current_game.get_player_race(player_name)} of {player_name}"
                        logger.debug(msg)
                        #self.processMessageForOpenAI(msg, "in_game")
                        processMessageForOpenAI(self, msg,  "in_game", logger, contextHistory)
                    break  # avoid processingMessageForOpenAI again below

    except Exception as e:
        logger.debug(f"error with find if player exists: {e}")
    return game_player_names