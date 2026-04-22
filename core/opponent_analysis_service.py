"""
Opponent Analysis Service - Extracted from game_started_handler for reusability.
Can be called from:
1. game_started (automatic when game starts)
2. please preview (manual command using last replay data)
"""

import logging

from settings import config
import utils.tokensArray as tokensArray
from api.chat_utils import processMessageForOpenAI
from utils.time_utils import calculate_time_ago
from utils.streamer_record_parse import parse_streamer_record_vs_opponent

from core.pregame_intel import PreGameBrief, run_known_opponent_pregame
from core.random_opponent_intel import gather_concrete_race_intel_for_random_opponent
from core.pregame_matchup_blurb import replay_h2h_streamer_vs_opponent

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

    def analyze_opponent(
        self,
        opponent_name: str,
        opponent_race: str,
        streamer_race: str,
        current_map: str = "Unknown",
        context_history: list = None,
        *,
        inline_saved_notes_in_last_meeting: bool = False,
    ):
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

        if str(opponent_race).strip().lower() == "random":
            (
                random_intel,
                random_canonical,
                primary_row,
                merged_comments_rb,
                _first_build,
            ) = gather_concrete_race_intel_for_random_opponent(
                self.db, opponent_name, streamer_race, logger
            )
            if random_intel:
                return self._analyze_known_opponent(
                    random_canonical,
                    opponent_race,
                    streamer_race,
                    current_map,
                    primary_row,
                    context_history,
                    inline_saved_notes_in_last_meeting=inline_saved_notes_in_last_meeting,
                    random_race_intel=random_intel,
                    merged_comments_override=merged_comments_rb,
                    lookup_name_original=opponent_name,
                )
            result = None
        else:
            result = self.db.check_player_and_race_exists(opponent_name, opponent_race)
        logger.debug(f"Result for player check: {result}")

        if result is not None:
            # Opponent found in DB - analyze previous games
            return self._analyze_known_opponent(
                opponent_name,
                opponent_race,
                streamer_race,
                current_map,
                result,
                context_history,
                inline_saved_notes_in_last_meeting=inline_saved_notes_in_last_meeting,
            )
        else:
            # New opponent
            return self._handle_new_opponent(
                opponent_name, opponent_race, streamer_race, context_history
            )

    def _analyze_known_opponent(
        self,
        opponent_name: str,
        opponent_race: str,
        streamer_race: str,
        current_map: str,
        db_result: dict,
        context_history: list,
        *,
        inline_saved_notes_in_last_meeting: bool = False,
        random_race_intel: tuple = (),
        merged_comments_override: list = None,
        lookup_name_original: str = None,
    ) -> bool:
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

        # Canonical ladder name (DB SC2_UserId) vs replay/client spelling (e.g. diacritics).
        if random_race_intel:
            original_opponent_for_hints = lookup_name_original or opponent_name
            canonical_opponent = opponent_name
            logger.debug(
                "random opponent intel: canonical=%r hints_original=%r",
                canonical_opponent,
                original_opponent_for_hints,
            )
        else:
            original_opponent_for_hints = opponent_name
            not_alias = tokensArray.find_master_name(original_opponent_for_hints)
            canonical_opponent = not_alias if not_alias is not None else original_opponent_for_hints
            if not_alias is not None:
                logger.debug(f"found alias: {not_alias} for {original_opponent_for_hints}")

        def _opponent_sc2_from_row(row: dict):
            for sn in config.SC2_PLAYER_ACCOUNTS:
                p1 = str(row.get("Player1_Name", ""))
                p2 = str(row.get("Player2_Name", ""))
                sll = sn.lower()
                if p1.lower() == sll:
                    return p2
                if p2.lower() == sll:
                    return p1
            return None

        opp_sc2_from_row = _opponent_sc2_from_row(db_result)

        # Get player records (win/loss)
        raw_records = self.db.get_player_records(canonical_opponent)
        logger.debug(f"[RECORD DEBUG] Raw records for {canonical_opponent}: {raw_records}")

        record_vs = parse_streamer_record_vs_opponent(raw_records)
        logger.debug(f"[RECORD] Parsed vs streamer accounts: {record_vs}")

        if random_race_intel:
            first_few_build_steps = None
        else:
            first_few_build_steps = self.db.extract_opponent_build_order(
                canonical_opponent, opponent_race, streamer_race
            )

        if canonical_opponent != original_opponent_for_hints:
            if db_result.get('Replay_Summary') and isinstance(db_result['Replay_Summary'], str):
                db_result['Replay_Summary'] = db_result['Replay_Summary'].replace(
                    original_opponent_for_hints, canonical_opponent
                )
            if first_few_build_steps and isinstance(first_few_build_steps, list):
                first_few_build_steps = [
                    item.replace(original_opponent_for_hints, canonical_opponent)
                    for item in first_few_build_steps
                    if isinstance(item, str)
                ]

        opponent_name = canonical_opponent

        if record_vs is None:
            _hints = [original_opponent_for_hints]
            if str(opponent_name).strip().lower() != str(original_opponent_for_hints).strip().lower():
                _hints.append(opponent_name)
            record_vs = replay_h2h_streamer_vs_opponent(self.db, tuple(_hints))
            logger.debug(f"[RECORD DEBUG] record_vs from replay H2H fallback (preview/service): {record_vs}")

        # Comments keyed by SC2_UserId: canonical ladder id, else opponent id from this replay row.
        if merged_comments_override is not None:
            player_comments = merged_comments_override
        else:
            player_comments = self.db.get_player_comments(canonical_opponent, opponent_race)
            if not player_comments and opp_sc2_from_row and (
                opp_sc2_from_row.strip().lower() != canonical_opponent.strip().lower()
            ):
                player_comments = self.db.get_player_comments(opp_sc2_from_row, opponent_race)
        logger.info(
            "[opponent_analysis] get_player_comments rows=%d canonical=%r original=%r row_opp=%r race=%s",
            len(player_comments or []),
            canonical_opponent,
            original_opponent_for_hints,
            opp_sc2_from_row,
            opponent_race,
        )

        _lookup_hints = [original_opponent_for_hints]
        if str(opponent_name).strip().lower() != str(original_opponent_for_hints).strip().lower():
            _lookup_hints.append(opponent_name)

        display_opp_race = "Random" if random_race_intel else opponent_race
        brief = PreGameBrief(
            opponent_display_name=opponent_name,
            opponent_race=display_opp_race,
            streamer_current_race=streamer_race,
            streamer_race_compare=streamer_picked_race,
            today_streamer_race=streamer_picked_race,
            today_opponent_race=display_opp_race,
            db_result=db_result,
            how_long_ago=how_long_ago,
            record_vs=record_vs,
            player_comments=player_comments,
            first_few_build_steps=first_few_build_steps,
            opponent_lookup_hints=tuple(_lookup_hints),
            inline_saved_notes_in_last_meeting=inline_saved_notes_in_last_meeting,
            random_race_intel=random_race_intel,
        )
        run_known_opponent_pregame(
            self.twitch_bot,
            brief,
            logger,
            context_history,
            current_map,
            quiet_when_no_build_extract=False,
            db_override=self.db,
        )

        return True

    def _handle_new_opponent(self, opponent_name: str, opponent_race: str,
                             streamer_race: str, context_history: list) -> bool:
        """Handle a new opponent not in DB."""
        msg = "Restate this without missing any details: \n "
        msg += f"I think this is the first time {config.STREAMER_NICKNAME} is playing {opponent_name}, at least the {opponent_race} of {opponent_name}"
        logger.debug(msg)
        processMessageForOpenAI(self.twitch_bot, msg, "in_game", logger, context_history)
        return True
