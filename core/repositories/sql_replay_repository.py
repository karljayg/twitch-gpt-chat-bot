import logging
import asyncio
from typing import Any, Optional
from core.interfaces import IReplayRepository

logger = logging.getLogger(__name__)

class SqlReplayRepository(IReplayRepository):
    """Implementation of IReplayRepository using legacy MySQL wrapper"""
    def __init__(self, db: Any):
        self.db = db
        
    async def get_latest_replay(self) -> Optional[dict]:
        """Get the last inserted replay"""
        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self.db.get_latest_replay)
        except Exception as e:
            logger.error(f"Error getting latest replay: {e}")
            return None
    
    async def save_replay(self, replay_data: Any) -> bool:
        """Save replay data (summary string in legacy DB)"""
        try:
            loop = asyncio.get_running_loop()
            # Legacy insert_replay_info returns truthy on success
            return await loop.run_in_executor(None, self.db.insert_replay_info, replay_data)
        except Exception as e:
            logger.error(f"Error saving replay: {e}")
            return False
    
    async def update_comment(self, comment: str) -> bool:
        """Update player comment for the last replay"""
        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self.db.update_player_comments_in_last_replay, comment)
        except Exception as e:
            logger.error(f"Error updating comment: {e}")
            return False


