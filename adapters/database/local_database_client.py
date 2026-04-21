"""
Local Database Client

Wrapper around the existing Database class to implement IDatabaseClient interface.
Used when DB_MODE='local' for direct MySQL connection.
"""

from core.interfaces import IDatabaseClient
from models.mathison_db import Database
from typing import List, Dict, Optional, Any


class LocalDatabaseClient(IDatabaseClient):
    """
    Direct MySQL connection using the existing Database class.
    This wraps the current behavior in the new interface.
    """
    
    def __init__(self):
        self._db = Database()
    
    # ===== Player Operations =====
    
    def check_player_and_race_exists(self, player_name: str, player_race: str) -> Optional[Dict]:
        return self._db.check_player_and_race_exists(player_name, player_race)
    
    def check_player_exists(self, player_name: str) -> Optional[Dict]:
        return self._db.check_player_exists(player_name)
    
    def get_player_records(self, player_name: str) -> List[str]:
        return self._db.get_player_records(player_name)
    
    def get_player_comments(self, player_name: str, player_race: str) -> List[Dict]:
        return self._db.get_player_comments(player_name, player_race)
    
    def get_player_overall_records(self, player_name: str) -> str:
        return self._db.get_player_overall_records(player_name)
    
    def get_player_race_matchup_records(self, player_name: str) -> str:
        """Get race matchup records for a player"""
        return self._db.get_player_race_matchup_records(player_name)
    
    def get_head_to_head_matchup(self, player1: str, player2: str) -> List[str]:
        """Get head-to-head matchup records between two players"""
        return self._db.get_head_to_head_matchup(player1, player2)
    
    # ===== Replay Operations =====
    
    def get_last_replay_info(self) -> Optional[Dict]:
        return self._db.get_last_replay_info()
    
    def get_latest_replay(self) -> Optional[Dict]:
        """Get latest replay with processed data (opponent, map, result, etc.)"""
        return self._db.get_latest_replay()
    
    def get_replay_by_id(self, replay_id: int) -> Optional[Dict]:
        return self._db.get_replay_by_id(replay_id)

    def get_replay_by_recency_offset(self, offset: int) -> Optional[Dict]:
        if hasattr(self._db, 'get_replay_by_recency_offset'):
            return self._db.get_replay_by_recency_offset(offset)
        return None
    
    def get_games_for_last_x_hours(self, hours: int) -> List[str]:
        """Get games played in the last X hours"""
        return self._db.get_games_for_last_x_hours(hours)
    
    def extract_opponent_build_order(self, opponent_name: str, opp_race: str, 
                                     streamer_picked_race: str) -> Optional[List[str]]:
        return self._db.extract_opponent_build_order(opponent_name, opp_race, streamer_picked_race)
    
    def insert_replay_info(self, replay_summary: str) -> bool:
        """Insert replay information into database"""
        return self._db.insert_replay_info(replay_summary)
    
    def update_player_comments_in_last_replay(self, comment: str) -> bool:
        """Update player comment for the last replay"""
        return self._db.update_player_comments_in_last_replay(comment)

    def update_player_comments_by_replay_id(self, replay_id: int, comment: str) -> bool:
        """Update player comment for a specific ReplayId."""
        if hasattr(self._db, 'update_player_comments_by_replay_id'):
            return self._db.update_player_comments_by_replay_id(replay_id, comment)
        return False
    
    def save_player_comment_with_data(self, comment_data: Dict) -> bool:
        """Save full comment data to PlayerComments table with keywords, build_order, etc."""
        if hasattr(self._db, 'save_player_comment_with_data'):
            return self._db.save_player_comment_with_data(comment_data)
        return False
    
    def save_pattern_to_db(self, pattern_entry: Dict) -> bool:
        """Save pattern to PatternLearning table"""
        if hasattr(self._db, 'save_pattern_to_db'):
            return self._db.save_pattern_to_db(pattern_entry)
        return False

    # FSL lives in psistorm; local client is mathison-only — use DB_MODE=api for /api/v1/fsl/.
    def fsl_players_search(self, q: str, limit: int = 40) -> Dict[str, Any]:
        return {}

    def fsl_player_by_id(self, player_id: int) -> Optional[Dict[str, Any]]:
        return None

    def fsl_player_by_name_exact(self, name: str) -> Optional[Dict[str, Any]]:
        return None

    def fsl_teams_search(self, q: str, limit: int = 40) -> Dict[str, Any]:
        return {}

    def fsl_team_by_id(self, team_id: int) -> Optional[Dict[str, Any]]:
        return None

    def fsl_team_players(self, team_id: int) -> Dict[str, Any]:
        return {}

    def fsl_schedule(
        self,
        season: Optional[int] = None,
        week: Optional[int] = None,
        limit: int = 120,
    ) -> Dict[str, Any]:
        return {}

    def fsl_schedule_entry(self, schedule_id: int) -> Optional[Dict[str, Any]]:
        return None

    def fsl_schedule_match_links(self, schedule_id: int) -> Dict[str, Any]:
        return {}

    def fsl_team_league_season_summary(self, season: int) -> Dict[str, Any]:
        return {}

    def fsl_solo_division_season_standings(
        self, season: int, division: str
    ) -> Dict[str, Any]:
        return {}

    def fsl_matches(
        self,
        season: Optional[int] = None,
        player_name: Optional[str] = None,
        player_id: Optional[int] = None,
        opponent_name: Optional[str] = None,
        limit: int = 60,
    ) -> Dict[str, Any]:
        return {}

    def fsl_matches_h2h(
        self,
        player_name: str,
        opponent_name: str,
        season: Optional[int] = None,
    ) -> Dict[str, Any]:
        return {}

    def fsl_match_by_id(self, fsl_match_id: int) -> Optional[Dict[str, Any]]:
        return None

    def fsl_statistics_for_player(self, player_id: int) -> Dict[str, Any]:
        return {}

    def fsl_leaderboard_match_win_pct(
        self, min_matches: int = 10, limit: int = 15
    ) -> Dict[str, Any]:
        return {}

    def fsl_leaderboard_match_total_wins(
        self, min_matches: int = 1, limit: int = 15
    ) -> Dict[str, Any]:
        return {}

    def fsl_leaderboard_maps_won(self, limit: int = 15) -> Dict[str, Any]:
        return {}

    # ===== Connection Management =====
    
    def ensure_connection(self):
        return self._db.ensure_connection()
    
    def keep_connection_alive(self):
        return self._db.keep_connection_alive()
    
    # ===== Legacy Compatibility =====
    
    @property
    def cursor(self):
        return self._db.cursor
    
    @property
    def connection(self):
        return self._db.connection
    
    @property
    def logger(self):
        return self._db.logger

