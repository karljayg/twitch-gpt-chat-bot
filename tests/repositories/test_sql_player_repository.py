import pytest
from unittest.mock import MagicMock, AsyncMock

# Placeholder
class SqlPlayerRepository:
    def __init__(self, db):
        self.db = db
    async def get_player_stats(self, name):
        return self.db.get_player_overall_records(name)
    async def get_matchup_stats(self, name):
        return self.db.get_player_race_matchup_records(name)

@pytest.fixture
def mock_legacy_db():
    db = MagicMock()
    db.get_player_overall_records.return_value = "Stats..."
    db.get_player_race_matchup_records.return_value = "Matchups..."
    return db

@pytest.mark.asyncio
async def test_get_player_stats(mock_legacy_db):
    from core.repositories.sql_player_repository import SqlPlayerRepository
    repo = SqlPlayerRepository(mock_legacy_db)
    
    stats = await repo.get_player_stats("Player1")
    assert stats == "Stats..."
    mock_legacy_db.get_player_overall_records.assert_called_with("Player1")

@pytest.mark.asyncio
async def test_get_matchup_stats(mock_legacy_db):
    from core.repositories.sql_player_repository import SqlPlayerRepository
    repo = SqlPlayerRepository(mock_legacy_db)
    
    stats = await repo.get_matchup_stats("Player1")
    assert stats == "Matchups..."
    mock_legacy_db.get_player_race_matchup_records.assert_called_with("Player1")


