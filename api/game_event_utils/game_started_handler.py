from datetime import datetime
import pytz
from api.chat_utils import processMessageForOpenAI, msgToChannel
from api.ml_opponent_analyzer import analyze_opponent_for_game_start

from settings import config
import utils.tokensArray as tokensArray
from utils.time_utils import calculate_time_ago


def game_started(self, current_game, contextHistory, logger):
    logger.info("game_started_handler.game_started() called")
    # Clear conversation context at start of new game to prevent player name confusion between games
    contextHistory.clear()
    logger.debug("Cleared conversation context for new game")
    
    # Clear pattern learning context when new game starts OR if it's older than 5 minutes
    if hasattr(self, 'pattern_learning_context') and self.pattern_learning_context:
        import time
        context_age = time.time() - self.pattern_learning_context.get('timestamp', 0)
        if context_age > 300:  # 5 minutes
            logger.info(f"Clearing stale pattern learning context (age: {context_age/60:.1f} minutes)")
        self.pattern_learning_context = None
        logger.debug("Cleared pattern learning context for new game")
    
    # prevent the array brackets from being included
    game_player_names = ', '.join(current_game.get_player_names())
    
    # Validate that we have actual players before processing
    if current_game.total_players == 0 or not game_player_names or game_player_names.strip() == '':
        logger.debug(f"Ignoring game start event - no players detected (total_players: {current_game.total_players}, names: '{game_player_names}')")
        return game_player_names
    
    try:
        if current_game.total_players == 2:
            # 1v1 game
            logger.debug("1v1 game, checking the players")
            game_player_names = [name.strip()
                                    for name in game_player_names.split(',')]
            if config.STREAMER_NICKNAME not in game_player_names:
                # Observing mode - provide analysis of both players based on database records
                logger.debug(f"Observer mode: {config.STREAMER_NICKNAME} not playing, analyzing {game_player_names}")
                
                player1, player2 = game_player_names[0], game_player_names[1]
                player1_race = current_game.get_player_race(player1)
                player2_race = current_game.get_player_race(player2)
                
                # Get overall records for each player
                def get_simple_record(player_name):
                    """Get simple W-L record for a player"""
                    try:
                        query = """
                        SELECT 
                            SUM(CASE WHEN (r.Player1_Id = p.Id AND r.Player1_Result = 'Win') OR (r.Player2_Id = p.Id AND r.Player2_Result = 'Win') THEN 1 ELSE 0 END) AS Wins,
                            SUM(CASE WHEN (r.Player1_Id = p.Id AND r.Player1_Result = 'Lose') OR (r.Player2_Id = p.Id AND r.Player2_Result = 'Lose') THEN 1 ELSE 0 END) AS Losses
                        FROM 
                            Replays r
                        JOIN 
                            Players p ON r.Player1_Id = p.Id OR r.Player2_Id = p.Id
                        WHERE 
                            p.SC2_UserId = %s
                            AND r.GameType = '1v1'
                        GROUP BY 
                            p.SC2_UserId;
                        """
                        self.db.cursor.execute(query, (player_name,))
                        result = self.db.cursor.fetchone()
                        if result and result['Wins'] is not None:
                            return (result['Wins'], result['Losses'])
                        return None
                    except Exception as e:
                        logger.debug(f"Error getting record for {player_name}: {e}")
                        return None
                
                player1_record = get_simple_record(player1)
                player2_record = get_simple_record(player2)
                
                # Get head-to-head record
                head_to_head = self.db.get_head_to_head_matchup(player1, player2)
                
                # Build concise records message
                records_msg = ""
                if player1_record or player2_record:
                    records_parts = []
                    if player1_record:
                        records_parts.append(f"{player1} is {player1_record[0]}-{player1_record[1]}")
                    else:
                        records_parts.append(f"{player1} has no records")
                    
                    if player2_record:
                        records_parts.append(f"{player2} is {player2_record[0]}-{player2_record[1]}")
                    else:
                        records_parts.append(f"{player2} has no records")
                    
                    records_msg = f"In games I've watched, {', '.join(records_parts)} overall."
                
                # Add head-to-head if available (sum across all race matchups)
                if head_to_head and len(head_to_head) > 0:
                    # head_to_head is a list like: ["Player1 (Race1) vs Player2 (Race2), X wins - Y wins", ...]
                    # Sum up wins across all race matchups
                    import re
                    total_p1_wins = 0
                    total_p2_wins = 0
                    for matchup in head_to_head:
                        # Format: "Player1 (Race1) vs Player2 (Race2), X wins - Y wins"
                        match = re.search(r'(\d+)\s+wins?\s*-\s*(\d+)\s+wins?', matchup)
                        if match:
                            total_p1_wins += int(match.group(1))
                            total_p2_wins += int(match.group(2))
                    
                    if total_p1_wins > 0 or total_p2_wins > 0:
                        if records_msg:
                            records_msg += f" Versus each other, {player1} is {total_p1_wins}-{total_p2_wins} vs {player2}."
                        else:
                            records_msg = f"Versus each other, {player1} is {total_p1_wins}-{total_p2_wins} vs {player2}."
                
                # Build the message for OpenAI variation
                if records_msg:
                    msg = f"Match starting: {player1} ({player1_race}) vs {player2} ({player2_race}). {records_msg}"
                    msg += "\n\n[INSTRUCTIONS: Reword this message naturally while keeping ALL numbers and player names exactly the same. Keep it concise (under 200 characters). Focus ONLY on the two players competing. Do NOT reference the streamer. This is observer commentary only.]"
                else:
                    # No records available
                    msg = f"Match starting: {player1} ({player1_race}) vs {player2} ({player2_race})."
                    msg += "\n\n[INSTRUCTIONS: Provide natural commentary on this observed match. Focus ONLY on the two players competing. Do NOT reference the streamer. This is observer commentary only.]"
                
                processMessageForOpenAI(self, msg, "in_game", logger, contextHistory)
            else:
                # self.play_SC2_sound("start") # Moved to BotCore.handle_game_state (TDD architecture)
                player_accounts_lower = [name.lower() for name in config.SC2_PLAYER_ACCOUNTS]
                for player_name in game_player_names:
                    logger.debug(f"looking for: {player_name}")
                    if player_name.lower() not in player_accounts_lower:
                        player_current_race = current_game.get_player_race(player_name)
                        streamer_current_race = current_game.get_opponent_race(player_name)
                        logger.debug(f"checking DB for {player_name} as {player_current_race} versus {config.STREAMER_NICKNAME} as any race, even tho {config.STREAMER_NICKNAME} is {streamer_current_race} in this current game")

                        # look for player with same name and race as this current game in the database
                        logger.debug(f"checking if {player_name} as {player_current_race} is in the DB")
                        result = self.db.check_player_and_race_exists(player_name, player_current_race)
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
                            # Calculate how long ago using shared utility
                            how_long_ago = calculate_time_ago(result['Date_Played'])

                            logger.debug(f"checking DB for last game where player versus {config.STREAMER_NICKNAME} was in same matchup of {player_current_race} versus {streamer_current_race} ")

                            # do this before alias substitutions, since we are only altering speaking/chat, not when searching for actual player name in DB records
                            raw_records = self.db.get_player_records(player_name)
                            logger.debug(f"[RECORD DEBUG] Raw records for {player_name}: {raw_records}")
                            
                            # Parse the row that matches KJ (don't just assume first row)
                            opponent_wins = 0
                            opponent_losses = 0
                            import re
                            if raw_records:
                                # Find the row that contains the streamer's name
                                streamer_row = None
                                for row in raw_records:
                                    # Check if this row is vs the streamer (case-insensitive)
                                    if config.STREAMER_NICKNAME.lower() in row.lower():
                                        streamer_row = row
                                        break
                                
                                if streamer_row:
                                    logger.debug(f"[RECORD DEBUG] Found row vs {config.STREAMER_NICKNAME}: {streamer_row}")
                                    # Parse: "SirMalagant, KJ, 129 wins, 203 losses"
                                    match = re.search(r'(\d+)\s+wins?,\s*(\d+)\s+losses?', streamer_row)
                                    if match:
                                        opponent_wins = int(match.group(1))
                                        opponent_losses = int(match.group(2))
                                        logger.debug(f"[RECORD DEBUG] Parsed: opponent has {opponent_wins} wins, {opponent_losses} losses vs {config.STREAMER_NICKNAME}")
                                else:
                                    logger.warning(f"[RECORD DEBUG] No record found for {player_name} vs {config.STREAMER_NICKNAME}")
                            
                            player_record = "past results:\n" + '\n'.join(raw_records)

                            # get the defined amount of build steps of the opponent with same race matchup from config.BUILD_ORDER_COUNT_TO_ANALYZE
                            first_few_build_steps = self.db.extract_opponent_build_order(player_name, player_current_race, streamer_current_race)

                            # if streamer is Random, then the last replay retrieved from previous query is the one to use
                            # use the last replay retrieved from previous query for Random, no need to requery coz the race doesn't matter since SC2 does not save 'Random' race in replay
                            # just the actual resulting race, to Random ->   Z, T, or P only in replay
                            # NOTE: first_few_build_steps should remain None if extract_opponent_build_order returns None
                            # Do NOT set it to result (which is a dict) - that would cause raw DB fields to be sent

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

                            # Fetch comments for the player on actual current name, not alias
                            player_comments = self.db.get_player_comments(current_player_name, player_current_race)

                            # Check if there are comments
                            if not player_comments:
                                logger.debug(f"No games with comments found for player '{current_player_name}' and race '{player_current_race}'.")
                                
                                # ML Analysis: Only run if NO player comments exist (use inferred patterns as fallback)
                                try:
                                    current_map = getattr(current_game, 'map', 'Unknown')
                                    logger.debug(f"Running ML pattern analysis for {player_name} (no player comments available)")
                                    analyze_opponent_for_game_start(
                                        player_name, player_current_race, current_map, 
                                        self, logger, contextHistory
                                    )
                                except Exception as e:
                                    logger.error(f"Error in ML opponent analysis: {e}")
                            else:
                                # Build the message string for OpenAI with enhanced SC2 focus and anti-hallucination measures
                                num_comment_games = len(player_comments)
                                # Calculate total games vs this opponent (wins + losses)
                                total_games = opponent_wins + opponent_losses
                                
                                # Sort comments by date (most recent first)
                                sorted_comments = sorted(player_comments, key=lambda x: x.get('date_played', ''), reverse=True)
                                
                                # Get the most recent game's details
                                most_recent = sorted_comments[0] if sorted_comments else None
                                recent_date_str = most_recent.get('date_played', 'unknown') if most_recent else 'unknown'
                                recent_date = calculate_time_ago(recent_date_str)
                                recent_comment = most_recent.get('player_comments', 'unknown strategy') if most_recent else 'unknown'
                                recent_map = most_recent.get('map', 'unknown map') if most_recent else 'unknown'
                                
                                # Format: Start with most recent game, then summarize others
                                if num_comment_games == 1:
                                    format_instruction = f"6. START your response with: 'Last game vs this opponent was {recent_date}: {recent_comment} on {recent_map}. '\n"
                                elif num_comment_games == 2:
                                    format_instruction = f"6. START your response with: 'Last game ({recent_date}): {recent_comment}. There is 1 other memorable game where the opponent '\n"
                                else:
                                    other_count = num_comment_games - 1
                                    format_instruction = f"6. START your response with: 'Last game ({recent_date}): {recent_comment}. There are {other_count} other memorable games (out of {total_games} total) where the opponent '\n"
                                
                                msg = "As a StarCraft 2 expert, analyze these previous game comments about the opponent. "
                                msg += "IMPORTANT: Use ONLY the data provided below - do NOT make assumptions or add information not present. \n\n"
                                msg += "Instructions:\n"
                                msg += "1. Extract ONLY the opponent's behavior: their build orders, strategies, unit compositions, timing, patterns\n"
                                msg += "2. IGNORE any advice, counter-strategies, or responses mentioned (e.g., 'kill with X', 'counter with Y')\n"
                                msg += "3. Use proper SC2 terminology (e.g., 'early game aggression', 'macro-focused', 'tech rush', 'timing attack')\n"
                                msg += "4. If opponent's units/buildings are mentioned, reference them accurately\n"
                                msg += "5. Keep summary under 300 characters\n"
                                msg += format_instruction
                                msg += "7. DO NOT use bullet points (-) or multiple sentences - TWO sentences max\n"
                                msg += "8. DO NOT mention units/buildings that are NOT explicitly mentioned in the comments below\n\n"
                                msg += "Previous game data (sorted by date, most recent first):\n"
                                msg += "-----\n"

                                # Add player comments to the message (already sorted)
                                for comment in sorted_comments:
                                    msg += (
                                        f"Comment: {comment['player_comments']}\n"
                                        f"Map: {comment['map']}\n"
                                        f"Date: {comment['date_played']}\n"
                                        f"Duration: {comment['game_duration']}\n"
                                        f"---\n"
                                    )

                                msg += "-----\n"
                                msg += "Based ONLY on the above data, provide a StarCraft 2-focused summary:\n"
                                msg += "CRITICAL: Describe ONLY what the opponent does (their builds, strategies, patterns). "
                                msg += "Do NOT give advice on how to respond or counter. "
                                msg += "Do NOT mention units/buildings not explicitly listed in the comments above."

                                # Get base response from OpenAI directly
                                from api.chat_utils import send_prompt_to_openai
                                try:
                                    completion = send_prompt_to_openai(msg)
                                    if completion.choices[0].message is not None:
                                        base_response = completion.choices[0].message.content
                                        
                                        # Remove "player comments warning" if present
                                        base_response = base_response.replace("player comments warning", "").strip()
                                        
                                        # Now vary the message while keeping all details and the specific format
                                        variation_msg = f"Rewrite this StarCraft 2 analysis message with different wording, but keep ALL the same details and the specific format:\n\n"
                                        variation_msg += f"{base_response}\n\n"
                                        variation_msg += "CRITICAL Requirements:\n"
                                        variation_msg += "1. You MUST start with the MOST RECENT game's date and strategy (e.g., 'Last game (2024-12-15): cannon rush. ...')\n"
                                        variation_msg += "2. Then mention other games if any exist\n"
                                        variation_msg += "3. You MUST mention what the opponent did in those previous games\n"
                                        variation_msg += "4. Use different phrasing and sentence structure for the rest\n"
                                        variation_msg += "5. Keep ALL the same details (dates, strategies, all patterns mentioned)\n"
                                        variation_msg += "6. Keep it under 300 characters\n"
                                        variation_msg += "7. TWO sentences max\n"
                                        variation_msg += "8. Do NOT add or remove any information\n"
                                        variation_msg += "9. Examples of good format:\n"
                                        variation_msg += "   - 'Last game (2024-12-15): cannon rush on Goldenaura. 3 other notable games showed DT rush and charge lot aggression.'\n"
                                        variation_msg += "   - 'Most recent (2024-12-10): ling bane all-in. Previously did roach timing and muta harass.'\n"
                                        
                                        # Get varied response
                                        variation_completion = send_prompt_to_openai(variation_msg)
                                        if variation_completion.choices[0].message is not None:
                                            varied_response = variation_completion.choices[0].message.content
                                            # Add "player comments warning" back for TTS trigger (but it will be removed in msgToChannel)
                                            varied_response = varied_response + " player comments warning"
                                            # Send the varied response to chat
                                            msgToChannel(self, varied_response, logger)
                                        else:
                                            # Fallback to base response if variation fails
                                            base_response = base_response + " player comments warning"
                                            msgToChannel(self, base_response, logger)
                                    else:
                                        # Fallback: use processMessageForOpenAI if direct call fails
                                        processMessageForOpenAI(self, msg, "last_time_played", logger, contextHistory)
                                except Exception as e:
                                    logger.error(f"Error getting/varying player comment analysis: {e}")
                                    # Fallback: use processMessageForOpenAI if direct call fails
                                    processMessageForOpenAI(self, msg, "last_time_played", logger, contextHistory)                     
                              
                            # Check if the previous game had the same matchup as current game
                            # Extract previous game's races from result
                            prev_player1_race = result.get('Player1_Race', '')
                            prev_player2_race = result.get('Player2_Race', '')
                            prev_player1_name = result.get('Player1_Name', '')
                            
                            # Determine streamer's race in the previous game
                            streamer_accounts = [name.lower() for name in config.SC2_PLAYER_ACCOUNTS]
                            if prev_player1_name.lower() in streamer_accounts:
                                prev_streamer_race = prev_player1_race
                            else:
                                prev_streamer_race = prev_player2_race
                            
                            # Check if matchup is different
                            same_matchup = (prev_streamer_race.lower() == streamer_picked_race.lower())
                            
                            msg = "Do these 2: \n"
                            if not same_matchup:
                                # Different matchup - note this clearly
                                msg += f"NOTE: The previous game was {prev_streamer_race}v{player_current_race}, but TODAY's game is {streamer_picked_race}v{player_current_race}. "
                                msg += f"When describing the previous game, use the CORRECT races from that game (previous matchup was {prev_streamer_race}v{player_current_race}). "
                            
                            if streamer_picked_race == "Random":
                                msg += f"Mention all details here, do not exclude any info: Even tho {config.STREAMER_NICKNAME} is Random, the last time he played the {player_current_race} player " 
                            else:
                                msg += f"Mention all details here, do not exclude any info: The last time {config.STREAMER_NICKNAME} played the {player_current_race} player "                                 
                            msg += f"{player_name} was {how_long_ago} in {{Map name}},"
                            msg += f" a {{Win/Loss for {config.STREAMER_NICKNAME}}} in {{game duration}}. \n"
                            msg += f"CRITICAL: In the replay summary below, {config.STREAMER_NICKNAME} is YOUR player. {player_name} is the OPPONENT. "
                            msg += f"When mentioning units/buildings, make sure you correctly identify which player built them. "
                            msg += f"Look at the section headers (e.g., '{config.STREAMER_NICKNAME}'s Build Order' vs '{player_name}'s Build Order'). "
                            if same_matchup:
                                msg += f"RACE CONSTRAINT: {config.STREAMER_NICKNAME} is {streamer_picked_race}, {player_name} is {player_current_race}. "
                                msg += f"ONLY mention units that exist for these races. Do NOT mention units from other races. "
                            else:
                                msg += f"In the PREVIOUS game: {config.STREAMER_NICKNAME} was {prev_streamer_race}, {player_name} was {player_current_race}. Use these races. "
                            msg += "As a StarCraft 2 expert, comment on last game summary. Be concise with only 2 sentences total of 25 words or less. \n"
                            msg += "-----\n"
                            msg += f" \n {result['Replay_Summary']} \n"
                            processMessageForOpenAI(self, msg, "last_time_played", logger, contextHistory)

                            # if there is a previous game with same race matchup
                            if first_few_build_steps is not None:
                                # Apply abbreviations to build order before sending to OpenAI
                                from utils.sc2_abbreviations import abbreviate_unit_name
                                
                                # Parse "Unit at Supply" format and abbreviate
                                abbreviated_steps = []
                                for step in first_few_build_steps:
                                    # Parse "Probe at 12" format
                                    parts = step.split(" at ")
                                    if len(parts) == 2:
                                        unit_name = parts[0]
                                        abbreviated_steps.append(abbreviate_unit_name(unit_name))
                                    else:
                                        abbreviated_steps.append(step)
                                
                                # Group consecutive duplicates with counts
                                grouped_build = []
                                prev_unit = None
                                count = 0
                                for unit in abbreviated_steps:
                                    if unit == prev_unit:
                                        count += 1
                                    else:
                                        if prev_unit:
                                            if count > 1:
                                                grouped_build.append(f"{prev_unit} x{count}")
                                            else:
                                                grouped_build.append(prev_unit)
                                        prev_unit = unit
                                        count = 1
                                # Add last unit
                                if prev_unit:
                                    if count > 1:
                                        grouped_build.append(f"{prev_unit} x{count}")
                                    else:
                                        grouped_build.append(prev_unit)
                                
                                abbreviated_build_string = ", ".join(grouped_build)
                                
                                # Merged prompt: List units/buildings/spells only, no intent speculation
                                msg = f"CRITICAL: Analyze ONLY the OPPONENT {player_name}'s build (NOT {config.STREAMER_NICKNAME}'s).\n"
                                msg += f"Build order (abbreviated): {abbreviated_build_string}\n\n"
                                msg += f"Requirements:\n"
                                msg += f"1. List ONLY units/buildings/spells that appear in the build order above - do NOT guess or infer units not shown\n"
                                msg += f"2. State simple facts - do NOT speculate on purpose, intent, or strategy\n"
                                msg += f"3. Do NOT use phrases like 'for aggression', 'timing attack', 'all-in', 'pressure', 'rush', 'bust', or any intent guessing\n"
                                msg += f"4. Example outputs (CORRECT):\n"
                                msg += f"   - '2 base Baneling Nest, Zergling Speed, Zerglings'\n"
                                msg += f"   - '3 base Roach Warren, Roaches, Ravagers'\n"
                                msg += f"   - '2 base Stargate, Oracle, Adept'\n"
                                msg += f"5. Example outputs (WRONG - DO NOT DO THIS):\n"
                                msg += f"   - 'Fast expand into roach timing' (speculates intent)\n"
                                msg += f"   - 'Gateway expand into blink stalker pressure' (uses strategy terms)\n"
                                msg += f"   - '2 base banshee into mech turtle' (speculates purpose)\n"
                                msg += f"6. DO NOT mention {config.STREAMER_NICKNAME}'s play - ONLY describe {player_name}'s build\n"
                                msg += f"7. DO NOT use bullet points or multiple sentences - ONE sentence only (max 25 words)\n"
                                msg += f"8. DO NOT mention units that are NOT in the build order above\n"
                                processMessageForOpenAI(self, msg, "last_time_played", logger, contextHistory)
                            else:
                                if streamer_picked_race == "Random":
                                    msg = f"restate this:  good luck playing {player_name} in this {streamer_picked_race} versus {player_current_race} matchup.  Random is tricky."                                    
                                else:
                                    msg = f"restate this with all details: This is the first time {config.STREAMER_NICKNAME} played {player_name} in this {streamer_picked_race} versus {player_current_race} matchup."
                                processMessageForOpenAI(self, msg, "last_time_played", logger, contextHistory)

                            # Calculate YOUR record (invert opponent's wins/losses)
                            your_wins = opponent_losses
                            your_losses = opponent_wins
                            
                            # Have AI just restate the calculated record in a natural way
                            msg = f"Restate this matchup record naturally in under 12 words:\n"
                            msg += f"{config.STREAMER_NICKNAME} has {your_wins} wins and {your_losses} losses versus {player_name}.\n"
                            
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
        
        else:
            # Team game (2v2, 3v3, 4v4, etc.)
            logger.debug(f"Team game detected: {current_game.total_players} players")
            
            player_list = [name.strip() for name in game_player_names.split(',')]
            
            # Check if streamer is actually playing (not observing)
            if config.STREAMER_NICKNAME not in player_list:
                logger.debug(f"Team game observer mode - {config.STREAMER_NICKNAME} not playing")
                msg = f"Team match starting with {current_game.total_players} players: {', '.join(player_list)}. "
                msg += "You are observing this team game. Provide brief 2-sentence commentary."
                processMessageForOpenAI(self, msg, "in_game", logger, contextHistory)
            else:
                # Streamer is playing - identify teammates
                logger.debug(f"{config.STREAMER_NICKNAME} is playing in team game")
                
                teammates = [p for p in player_list if p != config.STREAMER_NICKNAME]
                teammate_str = ', '.join(teammates) if teammates else "unknown"
                
                # Get races for all players
                player_races = {}
                for player in player_list:
                    try:
                        player_races[player] = current_game.get_player_race(player)
                    except:
                        player_races[player] = 'Unknown'
                
                streamer_race = player_races.get(config.STREAMER_NICKNAME, 'Unknown')
                
                # Build commentary message
                msg = f"Team game starting! {config.STREAMER_NICKNAME} ({streamer_race}) is teaming up with: {teammate_str}.\n"
                msg += f"All players: "
                for player in player_list:
                    msg += f"{player} ({player_races[player]}), "
                msg = msg.rstrip(', ') + ".\n\n"
                
                # Check database for previous games with teammates
                teammate_info = []
                for teammate in teammates:
                    teammate_race = player_races.get(teammate, 'Unknown')
                    record = self.db.check_player_and_race_exists(teammate, teammate_race)
                    if record:
                        last_played = record.get('Date_Played')
                        if last_played:
                            try:
                                time_diff = datetime.now() - last_played
                                days_ago = time_diff.days
                                if days_ago == 0:
                                    time_ago = "today"
                                elif days_ago == 1:
                                    time_ago = "yesterday"
                                else:
                                    time_ago = f"{days_ago} days ago"
                                teammate_info.append(f"Previously encountered {teammate} ({teammate_race}) - last seen {time_ago}")
                            except:
                                teammate_info.append(f"Previously encountered {teammate} ({teammate_race})")
                        else:
                            teammate_info.append(f"Previously encountered {teammate} ({teammate_race})")
                    else:
                        teammate_info.append(f"First time with {teammate} ({teammate_race})")
                
                if teammate_info:
                    msg += "Teammate history:\n"
                    for info in teammate_info:
                        msg += f"  • {info}\n"
                    msg += "\n"
                
                msg += "Based on the above, provide brief encouraging 2-sentence team commentary (max 30 words). "
                msg += f"Focus on the team composition and wish {config.STREAMER_NICKNAME} and teammates good luck."
                
                logger.debug(f"Sending team game commentary to OpenAI: {msg}")
                processMessageForOpenAI(self, msg, "in_game", logger, contextHistory)

    except Exception as e:
        logger.debug(f"error with find if player exists: {e}")
    
    # Convert list back to string if it was converted to list for processing
    if isinstance(game_player_names, list):
        game_player_names = ', '.join(game_player_names)
    
    return game_player_names
