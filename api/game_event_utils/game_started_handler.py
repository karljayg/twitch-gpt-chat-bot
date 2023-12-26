from datetime import datetime
import pytz
from ..chat_utils import processMessageForOpenAI

from settings import config



def game_started(self, current_game, contextHistory, logger):
    # prevent the array brackets from being included
    game_player_names = ', '.join(current_game.get_player_names())
    try:
        # if game_type == "1v1":
        if current_game.total_players == 2:
            logger.debug("1v1 game, checking the players")
            game_player_names = [name.strip()
                                    for name in game_player_names.split(',')]
            if config.STREAMER_NICKNAME not in game_player_names:
            # streamer is neither player, likely observing
                msg = f" \n New match starting between these players: {game_player_names} \n"
                processMessageForOpenAI(self, msg, "in_game", logger, contextHistory)
            else:
                self.play_SC2_sound("start")
                for player_name in game_player_names:
                    logger.debug(f"looking for: {player_name}")
                    if player_name != config.STREAMER_NICKNAME:
                        player_current_race = current_game.get_player_race(player_name)
                        streamer_current_race = current_game.get_opponent_race(player_name)
                        logger.debug(f"checking DB for {player_name} as {player_current_race} versus {config.STREAMER_NICKNAME} as any race, even tho {config.STREAMER_NICKNAME} is {streamer_current_race} in this current game")

                        # look for player with same name and race as this current game in the database
                        result = self.db.check_player_exists(player_name, player_current_race)
                        logger.debug(f"Result for player check: {result}")

                        if result is not None:
                            # determine streamer picked race, as the opponent's build will be based off of that, 
                            # and using Picked_Race in case it is Random
                            streamer_picked_race = "Unknown"

                            # Check if the streamer's name is Player1 or Player2 and assign picked_race
                            for streamer_name in config.SC2_PLAYER_ACCOUNTS:
                                if result['Player1_Name'] == streamer_name:
                                    streamer_picked_race = result['Player1_PickRace']
                                    break  # Exit loop if match found
                                elif result['Player2_Name'] == streamer_name:
                                    streamer_picked_race = result['Player2_PickRace']
                                    break  # Exit loop if match found

                            logger.debug(f"{config.STREAMER_NICKNAME} picked race: {streamer_picked_race}")

                            logger.debug(f"player with matching name and race of {player_current_race} exists in DB, last playing {config.STREAMER_NICKNAME} who was {streamer_picked_race} on {result['Date_Played']}")
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

                            logger.debug(f"checking DB for last game where player vs {config.STREAMER_NICKNAME} was in same race matchup: {player_current_race} vs {streamer_current_race} ")
                            first_30_build_steps = self.db.extract_opponent_build_order(player_name, player_current_race, streamer_current_race)
                                                        
                            player_record = "past results:\n" + '\n'.join(self.db.get_player_records(player_name))

                            msg = "Do these 2: \n"
                            msg += f"Mention all details here: {config.STREAMER_NICKNAME} as {streamer_picked_race} played the {player_current_race} player " 
                            msg += f"named {player_name} {how_long_ago} in {{Map name}},"
                            msg += f" a {{Win/Loss for {config.STREAMER_NICKNAME}}} in {{game duration}}. \n"
                            msg += f"As a StarCraft 2 expert, comment on last game summary. Be concise with only 2 sentences total of 25 words or less. \n"
                            msg += "-----\n"
                            msg += f" \n {result['Replay_Summary']} \n"
                            processMessageForOpenAI(self, msg, "last_time_played", logger, contextHistory)

                            # if there is a previous game with same race matchup
                            if first_30_build_steps is not None:
                                msg = f"The opponent {player_name}'s build order: {first_30_build_steps} \n"
                                msg += f"Do both but keep it short 25 words or less: \n"                                
                                msg += f"2. Look for any of these special buildings or units from the opponent's build order: roach warren, baneling nest, spire, nydus, hydra den, starport, forge, fusion core, ghost, factory, twilight, dark shrine, stargate, robotics \n"
                                msg += f"3. Mention any special buildings that exist in the build order for the opponent for same race matchup \n"
                                msg += f"but if there are no special buildings, mention that the opponent seemed to have a normal build order' \n"
                                processMessageForOpenAI(self, msg, "last_time_played", logger, contextHistory)

                                msg = f"Keep it concise in 400 characters or less: \n"
                                msg += "print the first 20 steps of the opponent's build order and group consecutive items together. Fox example, Probe 10 - Probe 11 - Probe 12 should be Probe (11-13). \n"
                                msg += "-----\n"
                                msg += f"{player_name}'s build order versus {config.STREAMER_NICKNAME}'s {streamer_picked_race}: {first_30_build_steps} \n"
                                msg += f"omit {config.STREAMER_NICKNAME}'s build order. \n"                                
                                processMessageForOpenAI(self, msg, "last_time_played", logger, contextHistory)
                            else:
                                msg = f"restate this with all details: This is the first time {config.STREAMER_NICKNAME} played {player_name} in this {streamer_picked_race} vs {player_current_race} matchup."
                                processMessageForOpenAI(self, msg, "last_time_played", logger, contextHistory)

                            msg = f"The CSV is listed as player1, player2, player 1 wins, player 1 losses. Respond with only 10 words with player1's name, and player1's total wins and total losses from the {player_record} \n"
                            processMessageForOpenAI(self, msg, "last_time_played", logger, contextHistory)

                        else:
                            msg = "Restate this without missing any details: \n "
                            msg += f"I think this is the first time {config.STREAMER_NICKNAME} is playing {player_name}, at least the {player_current_race} of {player_name}"
                            logger.debug(msg)
                            #self.processMessageForOpenAI(msg, "in_game")
                            processMessageForOpenAI(self, msg, "in_game", logger, contextHistory)
                        break  # avoid processingMessageForOpenAI again below

    except Exception as e:
        logger.debug(f"error with find if player exists: {e}")
    return game_player_names