from datetime import datetime
import pytz
from api.chat_utils import processMessageForOpenAI
from api.ml_opponent_analyzer import analyze_opponent_for_game_start

from settings import config
import utils.tokensArray as tokensArray



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

                        # ML Analysis: Generate strategic intelligence if opponent is known
                        try:
                            current_map = getattr(current_game, 'map', 'Unknown')
                            # Note: current_map is kept for logging but not used in ML analysis
                            analyze_opponent_for_game_start(
                                player_name, player_current_race, current_map, 
                                self, logger, contextHistory
                            )
                        except Exception as e:
                            logger.error(f"Error in ML opponent analysis: {e}")

                        # look for player with same name and race as this current game in the database
                        logger.debug(f"checking if {player_name} is in the DB independent of race because Random is not considered due to bug in replay parser")
                        # result = self.db.check_player_and_race_exists(player_name, player_current_race)
                        result = self.db.check_player_exists(player_name)
                        logger.debug(f"Result for player check: {result}")

                        if result is not None:
                            # determine streamer picked race, as the opponent's build will be based off of that, 
                            # and using Picked_Race in case it is Random
                            streamer_picked_race = "Unknown"

                            # Check if the streamer's name is Player1 or Player2 and assign picked_race
                            for streamer_name in config.SC2_PLAYER_ACCOUNTS:
                                if result['Player1_Name'].lower() == streamer_name.lower():
                                    streamer_picked_race = result['Player1_PickRace']
                                    break  # Exit loop if match found
                                elif result['Player2_Name'].lower() == streamer_name.lower():
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

                            logger.debug(f"checking DB for last game where player versus {config.STREAMER_NICKNAME} was in same matchup of {player_current_race} versus {streamer_current_race} ")

                            # do this before alias substitutions, since we are only altering speaking/chat, not when searching for actual player name in DB records
                            player_record = "past results:\n" + '\n'.join(self.db.get_player_records(player_name))

                            # get the defined amount of build steps of the opponent with same race matchup from config.BUILD_ORDER_COUNT_TO_ANALYZE
                            first_few_build_steps = self.db.extract_opponent_build_order(player_name, player_current_race, streamer_current_race)

                            # if streamer is Random, then the last replay retrieved from previous query is the one to use
                            # use the last replay retrieved from previous query for Random, no need to requery coz the race doesn't matter since SC2 does not save 'Random' race in replay
                            # just the actual resulting race, to Random ->   Z, T, or P only in replay
                            if(streamer_current_race == "Random"):
                                if first_few_build_steps is None:
                                    first_few_build_steps = result

                            # for speaking/chat purposes, do the substitutions
                            not_alias = tokensArray.find_master_name(player_name)
                            
                            # in case there is an alias, keep the current name for search
                            current_player_name = player_name

                            if not_alias is not None:
                                logger.debug(f"found alias: {not_alias} for {player_name}")

                                # Replace in Replay_Summary if it is a string
                                if result.get('Replay_Summary') is not None:
                                    logger.debug("Attempting to replace in Replay_Summary")
                                    if isinstance(result['Replay_Summary'], str):
                                        result['Replay_Summary'] = result['Replay_Summary'].replace(player_name, not_alias)

                                # Replace in player_record if it is a string
                                if player_record is not None:
                                    logger.debug(f"Attempting to replace in player_record: {player_record}")
                                    if isinstance(player_record, str):
                                        player_record = player_record.replace(player_name, not_alias)
                                        logger.debug(f"new player_record: {player_record}")

                                # Replace in first_few_build_steps if it is a list
                                if first_few_build_steps is not None:
                                    logger.debug("Attempting to replace in first_few_build_steps")
                                    if isinstance(first_few_build_steps, list):
                                        first_few_build_steps = [item.replace(player_name, not_alias) for item in first_few_build_steps if isinstance(item, str)]
                                player_name = not_alias
                            else:
                                logger.debug(f"no alias found for {player_name}")

                            if result['Player_Comments'] is not None:
                                msg = f"Restate this: 'The last game {how_long_ago} when {config.STREAMER_NICKNAME} played the opponent {player_name}: {result['Player_Comments']}'.\n"
                                msg += "\n After restating, append these characters exactly as is: ' player comments warning'. \n"
                                
                                # Send the prompt to OpenAI
                                processMessageForOpenAI(self, msg, "last_time_played", logger, contextHistory)

                            # Fetch comments for the player on actual current name, not alias
                            player_comments = self.db.get_player_comments(current_player_name, player_current_race)

                            # Check if there are comments
                            if not player_comments:
                                logger.debug(f"No games with comments found for player '{current_player_name}' and race '{player_current_race}'. Skipping OpenAI processing.")
                            else:
                                # Build the message string for OpenAI with enhanced SC2 focus and anti-hallucination measures
                                msg = "As a StarCraft 2 expert, analyze these previous game comments about the opponent. "
                                msg += "IMPORTANT: Use ONLY the data provided below - do NOT make assumptions or add information not present. \n\n"
                                msg += "Instructions:\n"
                                msg += "1. Focus on SC2-specific insights: build orders, strategies, unit compositions, timing, macro/micro patterns\n"
                                msg += "2. Use proper SC2 terminology (e.g., 'early game aggression', 'macro-focused', 'tech rush', 'timing attack')\n"
                                msg += "3. If comments mention specific units/buildings, reference them accurately\n"
                                msg += "4. Keep summary under 300 characters\n"
                                msg += "5. End with exactly: 'player comments warning'\n\n"
                                msg += "Previous game data:\n"
                                msg += "-----\n"

                                # Add player comments to the message
                                for comment in player_comments:
                                    msg += (
                                        f"Comment: {comment['player_comments']}\n"
                                        f"Map: {comment['map']}\n"
                                        f"Date: {comment['date_played']}\n"
                                        f"Duration: {comment['game_duration']}\n"
                                        f"---\n"
                                    )

                                msg += "-----\n"
                                msg += "Based ONLY on the above data, provide a StarCraft 2-focused summary:"

                                # Send the message to OpenAI
                                processMessageForOpenAI(self, msg, "last_time_played", logger, contextHistory)                     
                              
                            msg = "Do these 2: \n"
                            if streamer_picked_race == "Random":
                                msg += f"Mention all details here, do not exclude any info: Even tho {config.STREAMER_NICKNAME} is Random, the last time he was {streamer_picked_race} played the {player_current_race} player " 
                            else:
                                msg += f"Mention all details here, do not exclude any info: {config.STREAMER_NICKNAME} as {streamer_picked_race} played the {player_current_race} player "                                 
                            msg += f"{player_name} {how_long_ago} in {{Map name}},"
                            msg += f" a {{Win/Loss for {config.STREAMER_NICKNAME}}} in {{game duration}}. \n"
                            msg += "As a StarCraft 2 expert, comment on last game summary. Be concise with only 2 sentences total of 25 words or less. \n"
                            msg += "-----\n"
                            msg += f" \n {result['Replay_Summary']} \n"
                            processMessageForOpenAI(self, msg, "last_time_played", logger, contextHistory)

                            # if there is a previous game with same race matchup
                            if first_few_build_steps is not None:
                                msg = f"The opponent {player_name}'s build order: {first_few_build_steps} \n"
                                msg += "Keep it short 25 words or less: \n"
                                msg += "Mention any of these found in the opponent's build order:"
                                msg += "roach warren, baneling nest, spire, nydus, hydra den, starport, forge, fusion core, ghost, factory, twilight, dark shrine, stargate, robotics \n"
                                msg += "roach, baneling, muta, lurker, dark templar, immortal, void ray, oracle, charge, cyclone, liberator, banshee, battlecruiser, mine\n"
                                processMessageForOpenAI(self, msg, "last_time_played", logger, contextHistory)

                                msg = "Keep it concise in 400 characters or less: \n"
                                msg += f"<{player_name}>'s build order: "
                                msg += f"Summarize in chronological order:\n"
                                msg += "- Show the first 10-15 key steps in order\n"
                                msg += "- Group consecutive identical items with counts (e.g., 'SCV x3')\n"
                                msg += "- Use abbreviations for common units (SCV, Marine, Marauder, etc.)\n"
                                msg += "- Keep it under 150 characters total\n"
                                msg += "- Format: 'SCV x3, Barracks, SCV x2, Marine x2, Orbital, Marine x3, Reactor'\n"
                                msg += "- This shows: 3 SCVs, then Barracks, then 2 more SCVs, then 2 Marines, then Orbital, then 3 more Marines, then Reactor\n"
                                msg += "-----\n"
                                msg += f"{player_name}'s build order versus {config.STREAMER_NICKNAME}'s {streamer_picked_race}: {first_few_build_steps} \n"
                                msg += f"omit {config.STREAMER_NICKNAME}'s build order. \n"                                
                                processMessageForOpenAI(self, msg, "last_time_played", logger, contextHistory)
                            else:
                                if streamer_picked_race == "Random":
                                    msg = f"restate this:  good luck playing {player_name} in this {streamer_picked_race} versus {player_current_race} matchup.  Random is tricky."                                    
                                else:
                                    msg = f"restate this with all details: This is the first time {config.STREAMER_NICKNAME} played {player_name} in this {streamer_picked_race} versus {player_current_race} matchup."
                                processMessageForOpenAI(self, msg, "last_time_played", logger, contextHistory)

                            # Ensure we preserve the full player name and don't truncate the data
                            msg = f"IMPORTANT: The player name is '{player_name}' (exactly {len(player_name)} characters). Do NOT truncate or modify this name.\n\n"
                            msg += f"The CSV is listed as player1, player2, player 1 wins, player 1 losses. Respond with only 10 words with player1's name, and player1's total wins and total losses from the past results. Use the exact player name '{player_name}'. \n"
                            msg += f"Past results for {player_name}:\n{player_record}\n"
                            
                            # Debug logging to see what's being sent
                            logger.debug(f"Player name being sent to AI: '{player_name}' (length: {len(player_name)})")
                            logger.debug(f"Player record length: {len(player_record)}")
                            logger.debug(f"Full message length: {len(msg)}")
                            
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
    
    # Convert list back to string if it was converted to list for processing
    if isinstance(game_player_names, list):
        game_player_names = ', '.join(game_player_names)
    
    return game_player_names