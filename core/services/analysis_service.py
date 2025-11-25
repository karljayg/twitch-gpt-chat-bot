import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

class AnalysisService:
    """
    Service for analyzing opponents using ML/Replay data.
    Wraps legacy api.ml_opponent_analyzer.MLOpponentAnalyzer.
    """
    def __init__(self, analyzer: Any, db: Any):
        self.analyzer = analyzer
        self.db = db
        
    async def analyze_opponent(self, opponent_name: str, opponent_race: str = 'Unknown') -> Any:
        """
        Analyze an opponent and return analysis data.
        """
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(
                None, 
                self.analyzer.analyze_opponent_for_chat,
                opponent_name,
                opponent_race,
                logger,
                self.db
            )
        except Exception as e:
            logger.error(f"Error analyzing opponent: {e}")
            return None


