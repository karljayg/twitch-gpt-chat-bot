"""
Opponent Analysis Service - Extracted from game_started_handler for reusability.
Can be called from:
1. game_started (automatic when game starts)
2. please preview (manual command using last replay data)
"""

from datetime import datetime
import pytz
import re
import logging

from settings import config
import utils.tokensArray as tokensArray
from api.chat_utils import processMessageForOpenAI, msgToChannel
from api.ml_opponent_analyzer import analyze_opponent_for_game_start
from utils.time_utils import calculate_time_ago

logger = logging.getLogger(__name__)


class OpponentAnalysisService:
    """Service to analyze opponent history and provide pre-game intel."""
    
    def __init__(self, db, twitch_bot=None):
        """
        Args:
            db: Database instance for queries
            twitch_bot: TwitchBot instance (needed for processMessageForOpenAI)
        """
        self.db = db
        self.twitch_bot = twitch_bot
    
    def analyze_opponent(self, opponent_name: str, opponent_race: str, 
                         streamer_race: str, current_map: str = "Unknown",
                         context_history: list = None):
        """
        Run opponent analysis - looks up DB records, previous games, comments, etc.
        
        Args:
            opponent_name: Name of the opponent
            opponent_race: Race of the opponent (Zerg, Terran, Protoss)
            streamer_race: Race of the streamer in this game
            current_map: Current map name (for ML analysis)
            context_history: Conversation context (can be None for preview)
        
        Returns:
            bool: True if analysis was successful
        """
        if context_history is None:
            context_history = []
        
        if not self.twitch_bot:
            logger.error("OpponentAnalysisService requires twitch_bot for message sending")
            return False
        
        logger.info(f"Analyzing opponent: {opponent_name} ({opponent_race}) vs streamer ({streamer_race})")
        
        # Look up opponent in DB
        result = self.db.check_player_and_race_exists(opponent_name, opponent_race)
        logger.debug(f"Result for player check: {result}")
        
        if result is not None:
            # Opponent found in DB - analyze previous games
            return self._analyze_known_opponent(
                opponent_name, opponent_race, streamer_race, 
                current_map, result, context_history
            )
        else:
            # New opponent
            return self._handle_new_opponent(
                opponent_name, opponent_race, streamer_race, context_history
            )
    
    def _analyze_known_opponent(self, opponent_name: str, opponent_race: str,
                                 streamer_race: str, current_map: str,
                                 db_result: dict, context_history: list) -> bool:
        """Analyze a known opponent with DB history."""
        
        # Determine streamer's picked race from the previous game
        streamer_picked_race = "Unknown"
        for streamer_name in config.SC2_PLAYER_ACCOUNTS:
            if db_result['Player1_Name'].lower() == streamer_name.lower():
                streamer_picked_race = db_result['Player1_PickRace']
                break
            elif db_result['Player2_Name'].lower() == streamer_name.lower():
                streamer_picked_race = db_result['Player2_PickRace']
                break
        
        logger.debug(f"{config.STREAMER_NICKNAME} picked race in previous game: {streamer_picked_race}")
        
        # Calculate how long ago the last game was
        how_long_ago = calculate_time_ago(db_result['Date_Played'])
        
        # Get player records (win/loss)
        raw_records = self.db.get_player_records(opponent_name)
        logger.debug(f"[RECORD DEBUG] Raw records for {opponent_name}: {raw_records}")
        
        # Parse win/loss vs streamer
        opponent_wins, opponent_losses = self._parse_win_loss_record(raw_records)
        
        player_record = "past results:\n" + '\n'.join(raw_records) if raw_records else ""
        
        # Get build order from previous same-matchup game
        first_few_build_steps = self.db.extract_opponent_build_order(
            opponent_name, opponent_race, streamer_race
        )
        
        # Handle aliases for display
        current_player_name = opponent_name  # Keep original for DB lookups
        not_alias = tokensArray.find_master_name(opponent_name)
        
        if not_alias is not None:
            logger.debug(f"found alias: {not_alias} for {opponent_name}")
            
            # Replace in Replay_Summary
            if db_result.get('Replay_Summary') and isinstance(db_result['Replay_Summary'], str):
                db_result['Replay_Summary'] = db_result['Replay_Summary'].replace(opponent_name, not_alias)
            
            # Replace in player_record
            if player_record and isinstance(player_record, str):
                player_record = player_record.replace(opponent_name, not_alias)
            
            # Replace in build steps
            if first_few_build_steps and isinstance(first_few_build_steps, list):
                first_few_build_steps = [
                    item.replace(opponent_name, not_alias) 
                    for item in first_few_build_steps if isinstance(item, str)
                ]
            
            opponent_name = not_alias
        
        # Get player comments
        player_comments = self.db.get_player_comments(current_player_name, opponent_race)
        
        # Track if we sent player comments analysis (to avoid redundant last game summary)
        sent_player_comments_analysis = False
        
        # Send analysis messages
        if not player_comments:
            logger.debug(f"No games with comments found for player '{current_player_name}' and race '{opponent_race}'.")
            
            # Run ML analysis as fallback
            try:
                logger.debug(f"Running ML pattern analysis for {opponent_name} (no player comments)")
                analyze_opponent_for_game_start(
                    opponent_name, opponent_race, current_map,
                    self.twitch_bot, logger, context_history
                )
            except Exception as e:
                logger.error(f"Error in ML opponent analysis: {e}")
        else:
            # Send player comments analysis
            self._send_player_comments_analysis(
                opponent_name, opponent_race, player_comments,
                opponent_wins, opponent_losses, context_history
            )
            sent_player_comments_analysis = True
        
        # Send last game summary only if we didn't already send player comments analysis
        # (they both mention "last game" info and are redundant)
        if not sent_player_comments_analysis:
            self._send_last_game_summary(
                opponent_name, opponent_race, streamer_race, streamer_picked_race,
                how_long_ago, db_result, context_history
            )
        
        # Send build order analysis if available
        if first_few_build_steps:
            self._send_build_order_analysis(
                opponent_name, first_few_build_steps, context_history
            )
        else:
            # First time in this matchup
            self._send_first_matchup_message(
                opponent_name, opponent_race, streamer_picked_race, streamer_race, context_history
            )
        
        # Send win/loss record
        your_wins = opponent_losses
        your_losses = opponent_wins
        logger.info(f"[RECORD] Sending win/loss record: {config.STREAMER_NICKNAME} has {your_wins} wins and {your_losses} losses vs {opponent_name}")
        msg = f"Restate this matchup record naturally in under 12 words:\n"
        msg += f"{config.STREAMER_NICKNAME} has {your_wins} wins and {your_losses} losses versus {opponent_name}.\n"
        logger.debug(f"[RECORD] OpenAI msg: {msg}")
        processMessageForOpenAI(self.twitch_bot, msg, "last_time_played", logger, context_history)
        logger.info(f"[RECORD] Win/loss record sent to OpenAI")
        
        return True
    
    def _handle_new_opponent(self, opponent_name: str, opponent_race: str,
                              streamer_race: str, context_history: list) -> bool:
        """Handle a new opponent not in DB."""
        msg = "Restate this without missing any details: \n "
        msg += f"I think this is the first time {config.STREAMER_NICKNAME} is playing {opponent_name}, at least the {opponent_race} of {opponent_name}"
        logger.debug(msg)
        processMessageForOpenAI(self.twitch_bot, msg, "in_game", logger, context_history)
        return True
    
    def _parse_win_loss_record(self, raw_records) -> tuple:
        """Parse win/loss record from raw records."""
        opponent_wins = 0
        opponent_losses = 0
        
        if raw_records:
            streamer_row = None
            for row in raw_records:
                if config.STREAMER_NICKNAME.lower() in row.lower():
                    streamer_row = row
                    break
            
            if streamer_row:
                logger.debug(f"[RECORD DEBUG] Found row vs {config.STREAMER_NICKNAME}: {streamer_row}")
                match = re.search(r'(\d+)\s+wins?,\s*(\d+)\s+losses?', streamer_row)
                if match:
                    opponent_wins = int(match.group(1))
                    opponent_losses = int(match.group(2))
                    logger.debug(f"[RECORD DEBUG] Parsed: opponent has {opponent_wins} wins, {opponent_losses} losses")
        
        return opponent_wins, opponent_losses
    
    def _send_player_comments_analysis(self, opponent_name: str, opponent_race: str,
                                         player_comments: list, opponent_wins: int,
                                         opponent_losses: int, context_history: list):
        """Send analysis based on player comments."""
        num_comment_games = len(player_comments)
        total_games = opponent_wins + opponent_losses
        
        # Sort comments by date (most recent first)
        sorted_comments = sorted(player_comments, key=lambda x: x.get('date_played', ''), reverse=True)
        
        # Get most recent game details
        most_recent = sorted_comments[0] if sorted_comments else None
        recent_date_str = most_recent.get('date_played', 'unknown') if most_recent else 'unknown'
        recent_date = calculate_time_ago(recent_date_str)
        recent_comment = most_recent.get('player_comments', 'unknown strategy') if most_recent else 'unknown'
        recent_map = most_recent.get('map', 'unknown map') if most_recent else 'unknown'
        
        # Format instruction based on count
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
        
        from api.chat_utils import send_prompt_to_openai
        try:
            completion = send_prompt_to_openai(msg)
            if completion.choices[0].message is not None:
                base_response = completion.choices[0].message.content
                base_response = base_response.replace("player comments warning", "").strip()
                
                # Vary the message
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
                
                variation_completion = send_prompt_to_openai(variation_msg)
                if variation_completion.choices[0].message is not None:
                    varied_response = variation_completion.choices[0].message.content
                    varied_response = varied_response + " player comments warning"
                    msgToChannel(self.twitch_bot, varied_response, logger)
                else:
                    base_response = base_response + " player comments warning"
                    msgToChannel(self.twitch_bot, base_response, logger)
            else:
                processMessageForOpenAI(self.twitch_bot, msg, "last_time_played", logger, context_history)
        except Exception as e:
            logger.error(f"Error getting/varying player comment analysis: {e}")
            processMessageForOpenAI(self.twitch_bot, msg, "last_time_played", logger, context_history)
    
    def _send_last_game_summary(self, opponent_name: str, opponent_race: str,
                                  streamer_race: str, streamer_picked_race: str,
                                  how_long_ago: str, db_result: dict,
                                  context_history: list):
        """Send summary of last game vs this opponent."""
        
        # Check if the previous game had the same matchup
        prev_player1_race = db_result.get('Player1_Race', '')
        prev_player2_race = db_result.get('Player2_Race', '')
        prev_player1_name = db_result.get('Player1_Name', '')
        
        streamer_accounts = [name.lower() for name in config.SC2_PLAYER_ACCOUNTS]
        if prev_player1_name.lower() in streamer_accounts:
            prev_streamer_race = prev_player1_race
        else:
            prev_streamer_race = prev_player2_race
        
        same_matchup = (prev_streamer_race.lower() == streamer_race.lower())
        
        msg = "Do these 2: \n"
        if not same_matchup:
            msg += f"NOTE: The previous game was {prev_streamer_race}v{opponent_race}, but TODAY's game is {streamer_race}v{opponent_race}. "
            msg += f"When describing the previous game, use the CORRECT races from that game. "
        
        msg += f"Mention all details here, do not exclude any info: The last time {config.STREAMER_NICKNAME} played the {opponent_race} player "
        msg += f"{opponent_name} was {how_long_ago} in {{Map name}},"
        msg += f" a {{Win/Loss for {config.STREAMER_NICKNAME}}} in {{game duration}}. \n"
        msg += f"CRITICAL: In the replay summary below, {config.STREAMER_NICKNAME} is YOUR player. {opponent_name} is the OPPONENT. "
        msg += f"When mentioning units/buildings, make sure you correctly identify which player built them. "
        
        if same_matchup:
            msg += f"RACE CONSTRAINT: {config.STREAMER_NICKNAME} is {streamer_race}, {opponent_name} is {opponent_race}. "
            msg += f"ONLY mention units that exist for these races. "
        else:
            msg += f"In the PREVIOUS game: {config.STREAMER_NICKNAME} was {prev_streamer_race}, {opponent_name} was {opponent_race}. Use these races. "
        
        msg += "As a StarCraft 2 expert, comment on last game summary. Be concise with only 2 sentences total of 25 words or less. \n"
        msg += "-----\n"
        msg += f" \n {db_result['Replay_Summary']} \n"
        processMessageForOpenAI(self.twitch_bot, msg, "last_time_played", logger, context_history)
    
    def _send_build_order_analysis(self, opponent_name: str, 
                                     first_few_build_steps: list,
                                     context_history: list):
        """Send analysis of opponent's build order from previous game."""
        from utils.sc2_abbreviations import abbreviate_unit_name
        
        # Parse and abbreviate build steps
        abbreviated_steps = []
        for step in first_few_build_steps:
            parts = step.split(" at ")
            if len(parts) == 2:
                unit_name = parts[0]
                abbreviated_steps.append(abbreviate_unit_name(unit_name))
            else:
                abbreviated_steps.append(step)
        
        # Group consecutive duplicates
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
        if prev_unit:
            if count > 1:
                grouped_build.append(f"{prev_unit} x{count}")
            else:
                grouped_build.append(prev_unit)
        
        abbreviated_build_string = ", ".join(grouped_build)
        
        msg = f"CRITICAL: Analyze ONLY the OPPONENT {opponent_name}'s build (NOT {config.STREAMER_NICKNAME}'s).\n"
        msg += f"Build order (abbreviated): {abbreviated_build_string}\n\n"
        msg += f"Requirements:\n"
        msg += f"1. List ONLY units/buildings/spells that appear in the build order above - do NOT guess or infer units not shown\n"
        msg += f"2. State simple facts - do NOT speculate on purpose, intent, or strategy\n"
        msg += f"3. Do NOT use phrases like 'for aggression', 'timing attack', 'all-in', 'pressure', 'rush', 'bust', or any intent guessing\n"
        msg += f"4. Example outputs (CORRECT):\n"
        msg += f"   - '2 base Baneling Nest, Zergling Speed, Zerglings'\n"
        msg += f"   - '3 base Roach Warren, Roaches, Ravagers'\n"
        msg += f"5. DO NOT mention {config.STREAMER_NICKNAME}'s play - ONLY describe {opponent_name}'s build\n"
        msg += f"6. ONE sentence only (max 25 words)\n"
        processMessageForOpenAI(self.twitch_bot, msg, "last_time_played", logger, context_history)
    
    def _send_first_matchup_message(self, opponent_name: str, opponent_race: str,
                                      streamer_picked_race: str, streamer_race: str,
                                      context_history: list):
        """Send message when no build order data is available for this matchup."""
        # Don't claim it's the "first time" - just note we don't have specific build data
        # This could be due to missing data, not actually first time
        logger.debug(f"No build order data found for {opponent_name} in {streamer_race}v{opponent_race} matchup")
        # Skip sending a message - the win/loss record and player comments already provide context

