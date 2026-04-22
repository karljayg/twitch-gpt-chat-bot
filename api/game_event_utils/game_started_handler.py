from datetime import datetime
import pytz
from api.chat_utils import processMessageForOpenAI, msgToChannel

from core.pregame_intel import PreGameBrief, run_known_opponent_pregame
from core.random_opponent_intel import gather_concrete_race_intel_for_random_opponent
from core.pregame_matchup_blurb import (
    build_dual_player_tidbit,
    build_streamer_vs_opponent_tidbit,
    clear_pregame_matchup_blurb,
    replay_h2h_streamer_vs_opponent,
    set_pregame_matchup_blurb,
)

from settings import config
import utils.tokensArray as tokensArray
from utils.time_utils import calculate_time_ago
from utils.streamer_record_parse import parse_streamer_record_vs_opponent


def game_started(self, current_game, contextHistory, logger):
    logger.info("game_started_handler.game_started() called")
    # Clear conversation context at start of new game to prevent player name confusion between games
    contextHistory.clear()
    logger.debug("Cleared conversation context for new game")
    clear_pregame_matchup_blurb(self)
    
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
                
                matchup_tidbit = build_dual_player_tidbit(self.db, player1, player2, logger)
                if matchup_tidbit:
                    set_pregame_matchup_blurb(self, matchup_tidbit)

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

                if matchup_tidbit:
                    if records_msg:
                        records_msg += f" {matchup_tidbit}"
                    else:
                        records_msg = matchup_tidbit
                
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
                        is_random_opp = (
                            str(player_current_race).strip().lower() == "random"
                        )
                        random_race_intel = tuple()
                        random_canonical = None
                        merged_comments_rb: list = []
                        first_build_rb = None
                        if is_random_opp:
                            (
                                random_race_intel,
                                random_canonical,
                                result,
                                merged_comments_rb,
                                first_build_rb,
                            ) = gather_concrete_race_intel_for_random_opponent(
                                self.db,
                                player_name,
                                streamer_current_race,
                                logger,
                            )
                            if not random_race_intel:
                                result = None
                        else:
                            result = self.db.check_player_and_race_exists(
                                player_name, player_current_race
                            )
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

                            if is_random_opp and random_race_intel:
                                # Random on ladder: DB stores actual spawn races (T/Z/P), never "Random".
                                original_opp = player_name
                                canonical_opp = random_canonical
                                current_player_name = original_opp
                                if canonical_opp.strip().lower() != original_opp.strip().lower():
                                    logger.debug(
                                        f"resolved ladder id {canonical_opp} for {original_opp} (random intel)"
                                    )

                                raw_records = self.db.get_player_records(canonical_opp)
                                logger.debug(f"[RECORD DEBUG] Raw records for {canonical_opp}: {raw_records}")

                                record_vs = parse_streamer_record_vs_opponent(raw_records)
                                logger.debug(f"[RECORD DEBUG] Parsed vs streamer accounts: {record_vs}")

                                player_record = "past results:\n" + '\n'.join(raw_records)

                                first_few_build_steps = None

                                if canonical_opp != original_opp:
                                    if result.get('Replay_Summary') is not None:
                                        logger.debug("Attempting to replace in Replay_Summary")
                                        if isinstance(result['Replay_Summary'], str):
                                            result['Replay_Summary'] = result['Replay_Summary'].replace(
                                                original_opp, canonical_opp
                                            )

                                    if player_record is not None:
                                        logger.debug(f"Attempting to replace in player_record: {player_record}")
                                        if isinstance(player_record, str):
                                            player_record = player_record.replace(original_opp, canonical_opp)
                                            logger.debug(f"new player_record: {player_record}")

                                player_name = canonical_opp

                                _opp_lookup_hints = [current_player_name]
                                if str(player_name).strip().lower() != str(
                                    current_player_name
                                ).strip().lower():
                                    _opp_lookup_hints.append(player_name)
                                _opp_lookup_tuple = tuple(_opp_lookup_hints)

                                if record_vs is None:
                                    record_vs = replay_h2h_streamer_vs_opponent(
                                        self.db, _opp_lookup_tuple
                                    )
                                    logger.debug(
                                        f"[RECORD DEBUG] record_vs from replay H2H fallback: {record_vs}"
                                    )

                                player_comments = merged_comments_rb

                                brief = PreGameBrief(
                                    opponent_display_name=player_name,
                                    opponent_race="Random",
                                    streamer_current_race=streamer_current_race,
                                    streamer_race_compare=streamer_picked_race,
                                    today_streamer_race=streamer_picked_race,
                                    today_opponent_race="Random",
                                    db_result=result,
                                    how_long_ago=how_long_ago,
                                    record_vs=record_vs,
                                    player_comments=player_comments,
                                    first_few_build_steps=first_few_build_steps,
                                    opponent_lookup_hints=_opp_lookup_tuple,
                                    random_race_intel=random_race_intel,
                                )
                            else:
                                # Resolve canonical ladder id (DB SC2_UserId) before records / build / comments.
                                original_opp = player_name
                                not_alias = tokensArray.find_master_name(original_opp)
                                canonical_opp = not_alias if not_alias is not None else original_opp
                                current_player_name = original_opp
                                if not_alias is not None:
                                    logger.debug(f"found alias: {not_alias} for {original_opp}")

                                raw_records = self.db.get_player_records(canonical_opp)
                                logger.debug(f"[RECORD DEBUG] Raw records for {canonical_opp}: {raw_records}")

                                record_vs = parse_streamer_record_vs_opponent(raw_records)
                                logger.debug(f"[RECORD DEBUG] Parsed vs streamer accounts: {record_vs}")

                                player_record = "past results:\n" + '\n'.join(raw_records)

                                first_few_build_steps = self.db.extract_opponent_build_order(
                                    canonical_opp, player_current_race, streamer_current_race
                                )

                                if canonical_opp != original_opp:
                                    if result.get('Replay_Summary') is not None:
                                        logger.debug("Attempting to replace in Replay_Summary")
                                        if isinstance(result['Replay_Summary'], str):
                                            result['Replay_Summary'] = result['Replay_Summary'].replace(
                                                original_opp, canonical_opp
                                            )

                                    if player_record is not None:
                                        logger.debug(f"Attempting to replace in player_record: {player_record}")
                                        if isinstance(player_record, str):
                                            player_record = player_record.replace(original_opp, canonical_opp)
                                            logger.debug(f"new player_record: {player_record}")

                                    if first_few_build_steps is not None:
                                        logger.debug("Attempting to replace in first_few_build_steps")
                                        if isinstance(first_few_build_steps, list):
                                            first_few_build_steps = [
                                                item.replace(original_opp, canonical_opp)
                                                for item in first_few_build_steps
                                                if isinstance(item, str)
                                            ]
                                player_name = canonical_opp
                                if not_alias is None:
                                    logger.debug(f"no alias found for {current_player_name}")

                                _opp_lookup_hints = [current_player_name]
                                if str(player_name).strip().lower() != str(
                                    current_player_name
                                ).strip().lower():
                                    _opp_lookup_hints.append(player_name)
                                _opp_lookup_tuple = tuple(_opp_lookup_hints)

                                if record_vs is None:
                                    record_vs = replay_h2h_streamer_vs_opponent(
                                        self.db, _opp_lookup_tuple
                                    )
                                    logger.debug(
                                        f"[RECORD DEBUG] record_vs from replay H2H fallback: {record_vs}"
                                    )

                                # Comments keyed by SC2_UserId: canonical name, else other player on this row.
                                player_comments = self.db.get_player_comments(player_name, player_current_race)
                                if not player_comments:
                                    p1n = str(result.get("Player1_Name", ""))
                                    p2n = str(result.get("Player2_Name", ""))
                                    opp_id = None
                                    for sn in config.SC2_PLAYER_ACCOUNTS:
                                        sl = sn.lower()
                                        if p1n.lower() == sl:
                                            opp_id = p2n
                                            break
                                        if p2n.lower() == sl:
                                            opp_id = p1n
                                            break
                                    if opp_id and opp_id.strip().lower() != str(player_name).strip().lower():
                                        player_comments = self.db.get_player_comments(opp_id, player_current_race)

                                brief = PreGameBrief(
                                    opponent_display_name=player_name,
                                    opponent_race=player_current_race,
                                    streamer_current_race=streamer_current_race,
                                    streamer_race_compare=streamer_picked_race,
                                    today_streamer_race=streamer_picked_race,
                                    today_opponent_race=player_current_race,
                                    db_result=result,
                                    how_long_ago=how_long_ago,
                                    record_vs=record_vs,
                                    player_comments=player_comments,
                                    first_few_build_steps=first_few_build_steps,
                                    opponent_lookup_hints=_opp_lookup_tuple,
                                )
                            current_map = getattr(current_game, "map", "Unknown")
                            set_pregame_matchup_blurb(
                                self,
                                build_streamer_vs_opponent_tidbit(
                                    self.db,
                                    player_name,
                                    _opp_lookup_tuple,
                                    logger,
                                ),
                            )
                            run_known_opponent_pregame(self, brief, logger, contextHistory, current_map)
                            
                        else:
                            # DB row missing can still mean we've seen them in pattern-learning file or loose records;
                            # never hint "first time" unless both are empty or we contradict ML / later messages.
                            raw_records_o = None
                            try:
                                raw_records_o = self.db.get_player_records(player_name)
                            except Exception as ex:
                                logger.debug(f"[RECORD DEBUG] get_player_records failed: {ex}")
                            record_vs_o = parse_streamer_record_vs_opponent(raw_records_o)
                            if record_vs_o is None:
                                record_vs_o = replay_h2h_streamer_vs_opponent(
                                    self.db, (player_name,)
                                )
                                logger.debug(
                                    f"[RECORD DEBUG] record_vs_o from replay H2H fallback: {record_vs_o}"
                                )

                            has_learning_history = False
                            try:
                                from api.ml_opponent_analyzer import get_ml_analyzer

                                ld = get_ml_analyzer().load_learning_data()
                                opponent_games = [
                                    c
                                    for c in ld.get("comments", [])
                                    if c.get("game_data", {}).get("opponent_name") == player_name
                                ]
                                has_learning_history = len(opponent_games) >= 1
                            except Exception as ex:
                                logger.debug(f"Learning-data history check skipped: {ex}")

                            has_db_records = bool(raw_records_o)
                            if has_learning_history or has_db_records:
                                set_pregame_matchup_blurb(
                                    self,
                                    build_streamer_vs_opponent_tidbit(
                                        self.db,
                                        player_name,
                                        (player_name,),
                                        logger,
                                    ),
                                )
                                msgToChannel(
                                    self,
                                    f"GLHF vs {player_name} ({player_current_race}).",
                                    logger,
                                )
                                min_h2h = int(getattr(config, "MIN_HEAD_TO_HEAD_GAMES_TO_SHOW_RECORD", 2))
                                if (
                                    record_vs_o is not None
                                    and (record_vs_o[0] + record_vs_o[1]) >= min_h2h
                                ):
                                    yw, yl = record_vs_o
                                    msgToChannel(
                                        self,
                                        f"{config.STREAMER_NICKNAME}'s record vs {player_name}: {yw}-{yl}.",
                                        logger,
                                    )
                            else:
                                set_pregame_matchup_blurb(
                                    self,
                                    build_streamer_vs_opponent_tidbit(
                                        self.db,
                                        player_name,
                                        (player_name,),
                                        logger,
                                    ),
                                )
                                msg = "Restate this without missing any details: \n "
                                msg += f"I think this is the first time {config.STREAMER_NICKNAME} is playing {player_name}, at least the {player_current_race} of {player_name}"
                                logger.debug(msg)
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
