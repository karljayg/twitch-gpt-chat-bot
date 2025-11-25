import logging
import asyncio
from typing import Optional, List
from core.interfaces import IPlayerRepository

logger = logging.getLogger(__name__)

class SqlPlayerRepository(IPlayerRepository):
    """Implementation of IPlayerRepository using legacy MySQL wrapper"""
    def __init__(self, db):
        self.db = db
        
    async def get_player_stats(self, player_name: str) -> Optional[str]:
        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self.db.get_player_overall_records, player_name)
        except Exception as e:
            logger.error(f"Error getting player stats: {e}")
            return None
            
    async def get_matchup_stats(self, player_name: str) -> Optional[str]:
        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self.db.get_player_race_matchup_records, player_name)
        except Exception as e:
            logger.error(f"Error getting matchup stats: {e}")
            return None

    async def get_player_records(self, player_name: str) -> List[str]:
        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self.db.get_player_records, player_name)
        except Exception as e:
            logger.error(f"Error getting player records: {e}")
            return []
