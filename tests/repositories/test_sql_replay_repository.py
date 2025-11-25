import pytest
from unittest.mock import MagicMock, AsyncMock
# from core.repositories.sql_replay_repository import SqlReplayRepository

# Placeholder
class SqlReplayRepository:
    def __init__(self, db):
        self.db = db
    async def get_latest_replay(self):
        return self.db.get_latest_replay()
    async def save_replay(self, data):
        return self.db.insert_replay_info(data)
    async def update_comment(self, comment):
        return self.db.update_player_comments_in_last_replay(comment)

@pytest.fixture
def mock_legacy_db():
    db = MagicMock()
    db.get_latest_replay.return_value = {"id": 1, "map": "Test Map"}
    db.insert_replay_info.return_value = True
    db.update_player_comments_in_last_replay.return_value = True
    return db

@pytest.mark.asyncio
async def test_get_latest_replay(mock_legacy_db):
    # Import real class once created
    from core.repositories.sql_replay_repository import SqlReplayRepository
    
    repo = SqlReplayRepository(mock_legacy_db)
    
    result = await repo.get_latest_replay()
    
    assert result["map"] == "Test Map"
    mock_legacy_db.get_latest_replay.assert_called_once()

@pytest.mark.asyncio
async def test_save_replay(mock_legacy_db):
    from core.repositories.sql_replay_repository import SqlReplayRepository
    
    repo = SqlReplayRepository(mock_legacy_db)
    await repo.save_replay("summary string")
    mock_legacy_db.insert_replay_info.assert_called_with("summary string")

@pytest.mark.asyncio
async def test_update_comment(mock_legacy_db):
    from core.repositories.sql_replay_repository import SqlReplayRepository
    
    repo = SqlReplayRepository(mock_legacy_db)
    await repo.update_comment("Nice game")
    mock_legacy_db.update_player_comments_in_last_replay.assert_called_with("Nice game")


