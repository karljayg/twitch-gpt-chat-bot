"""
Local Database Client

Wrapper around the existing Database class to implement IDatabaseClient interface.
Used when DB_MODE='local' for direct MySQL connection.
"""

from core.interfaces import IDatabaseClient
from models.mathison_db import Database
from typing import List, Dict, Optional


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
    
    # ===== Replay Operations =====
    
    def get_last_replay_info(self) -> Optional[Dict]:
        return self._db.get_last_replay_info()
    
    def get_replay_by_id(self, replay_id: int) -> Optional[Dict]:
        return self._db.get_replay_by_id(replay_id)
    
    def extract_opponent_build_order(self, opponent_name: str, opp_race: str, 
                                     streamer_picked_race: str) -> Optional[List[str]]:
        return self._db.extract_opponent_build_order(opponent_name, opp_race, streamer_picked_race)
    
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

