import pytest
from unittest.mock import MagicMock, AsyncMock
# from core.services.analysis_service import AnalysisService

# Placeholder
class AnalysisService:
    def __init__(self, analyzer, db):
        self.analyzer = analyzer
        self.db = db
        
    async def analyze_opponent(self, opponent_name, opponent_race):
        # Mock implementation for test loop until real file created
        import asyncio
        import logging
        logger = logging.getLogger("test")
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, 
            self.analyzer.analyze_opponent_for_chat,
            opponent_name,
            opponent_race,
            logger,
            self.db
        )

@pytest.fixture
def mock_analyzer():
    return MagicMock()

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.mark.asyncio
async def test_analyze_opponent(mock_analyzer, mock_db):
    from core.services.analysis_service import AnalysisService
    
    service = AnalysisService(mock_analyzer, mock_db)
    
    mock_analyzer.analyze_opponent_for_chat.return_value = {"summary": "He zerg rushes."}
    
    result = await service.analyze_opponent("Player1", "Zerg")
    
    assert result["summary"] == "He zerg rushes."
    mock_analyzer.analyze_opponent_for_chat.assert_called()


