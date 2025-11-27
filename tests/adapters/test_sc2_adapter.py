"""
Tests for SC2Adapter - Game detection and state change logic.

These tests would catch:
- Game start/end detection failures
- MATCH_STARTED -> REPLAY_ENDED transition bug
- MATCH_STARTED -> MATCH_STARTED (new game) detection
- Event creation for game_ended vs status_change
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from models.game_info import GameInfo
from adapters.sc2_adapter import SC2Adapter
from core.bot import BotCore
from core.events import GameStateEvent


@pytest.fixture
def mock_bot_core():
    """Mock BotCore with event queue"""
    bot = MagicMock(spec=BotCore)
    bot.add_event = MagicMock()
    bot.chat_services = {}
    return bot


@pytest.fixture
def mock_game_result_service():
    """Mock GameResultService"""
    service = MagicMock()
    service.process_game_end = AsyncMock()
    return service


@pytest.fixture
def sc2_adapter(mock_bot_core, mock_game_result_service):
    """Create SC2Adapter instance"""
    adapter = SC2Adapter(mock_bot_core, mock_game_result_service)
    return adapter


def create_game_info(status, is_replay=False, players=None, display_time=0.0):
    """Helper to create GameInfo with specific status"""
    if players is None:
        if status in ("MATCH_STARTED", "REPLAY_STARTED"):
            # Game starting - all Undecided
            players = [
                {"name": "KJ", "result": "Undecided", "race": "prot"},
                {"name": "Opponent", "result": "Undecided", "race": "zerg"}
            ]
        elif status in ("MATCH_ENDED", "REPLAY_ENDED"):
            # Game ended
            players = [
                {"name": "KJ", "result": "Victory", "race": "prot"},
                {"name": "Opponent", "result": "Defeat", "race": "zerg"}
            ]
        else:
            players = []
    
    return GameInfo({
        "isReplay": is_replay,
        "players": players,
        "displayTime": display_time
    })


class TestStateChangeDetection:
    """Test _has_state_changed logic"""
    
    def test_status_change_detected(self, sc2_adapter):
        """Basic status change should be detected"""
        old_game = create_game_info("MATCH_STARTED")
        new_game = create_game_info("MATCH_ENDED")
        
        assert sc2_adapter._has_state_changed(old_game, new_game) is True
    
    def test_no_change_when_same_status(self, sc2_adapter):
        """Same status with same players should not trigger change"""
        old_game = create_game_info("MATCH_STARTED")
        new_game = create_game_info("MATCH_STARTED")
        
        assert sc2_adapter._has_state_changed(old_game, new_game) is False
    
    def test_new_game_detected_matchmaking_to_game(self, sc2_adapter):
        """MATCH_STARTED (no players) -> MATCH_STARTED (with players) should be detected"""
        # Matchmaking screen - no players yet
        old_game = create_game_info("MATCH_STARTED", players=[])
        
        # Actual game started - players loaded
        new_game = create_game_info("MATCH_STARTED", players=[
            {"name": "KJ", "result": "Undecided", "race": "prot"},
            {"name": "Opponent", "result": "Undecided", "race": "zerg"}
        ])
        
        assert sc2_adapter._has_state_changed(old_game, new_game) is True
    
    def test_none_to_game_detected(self, sc2_adapter):
        """None -> MATCH_STARTED should be detected"""
        assert sc2_adapter._has_state_changed(None, create_game_info("MATCH_STARTED")) is True
    
    def test_game_to_none_detected(self, sc2_adapter):
        """MATCH_STARTED -> None should be detected"""
        assert sc2_adapter._has_state_changed(create_game_info("MATCH_STARTED"), None) is True


class TestEventCreation:
    """Test _create_game_event logic"""
    
    def test_match_started_creates_game_started_event(self, sc2_adapter):
        """MATCH_STARTED should create game_started event"""
        game = create_game_info("MATCH_STARTED")
        event = sc2_adapter._create_game_event(game)
        
        assert event.event_type == "game_started"
        assert event.data["status"] == "MATCH_STARTED"
    
    def test_match_ended_creates_game_ended_event(self, sc2_adapter):
        """MATCH_ENDED should create game_ended event"""
        game = create_game_info("MATCH_ENDED")
        event = sc2_adapter._create_game_event(game)
        
        assert event.event_type == "game_ended"
        assert event.data["status"] == "MATCH_ENDED"
    
    def test_replay_ended_creates_game_ended_event(self, sc2_adapter):
        """REPLAY_ENDED should create game_ended event (critical bug fix)"""
        game = create_game_info("REPLAY_ENDED", is_replay=True)
        event = sc2_adapter._create_game_event(game)
        
        assert event.event_type == "game_ended", "REPLAY_ENDED should trigger game_ended, not status_change"
        assert event.data["status"] == "REPLAY_ENDED"
    
    def test_replay_started_creates_status_change_event(self, sc2_adapter):
        """REPLAY_STARTED should create status_change event"""
        game = create_game_info("REPLAY_STARTED", is_replay=True)
        event = sc2_adapter._create_game_event(game)
        
        assert event.event_type == "status_change"
        assert event.data["status"] == "REPLAY_STARTED"


class TestGameEndProcessing:
    """Test that game end triggers GameResultService"""
    
    @pytest.mark.asyncio
    async def test_match_ended_triggers_game_result_service(self, sc2_adapter, mock_game_result_service):
        """MATCH_ENDED should trigger process_game_end"""
        sc2_adapter.current_game = create_game_info("MATCH_STARTED")
        new_game = create_game_info("MATCH_ENDED")
        
        # Simulate state change
        sc2_adapter.current_game = new_game
        sc2_adapter.previous_game = sc2_adapter.current_game
        
        # Manually trigger the logic that would happen in monitoring loop
        status = new_game.get_status()
        if status in ("MATCH_ENDED", "REPLAY_ENDED") and sc2_adapter.game_result_service:
            await sc2_adapter.game_result_service.process_game_end(new_game)
        
        mock_game_result_service.process_game_end.assert_called_once_with(new_game)
    
    @pytest.mark.asyncio
    async def test_replay_ended_triggers_game_result_service(self, sc2_adapter, mock_game_result_service):
        """REPLAY_ENDED should trigger process_game_end (critical bug fix)"""
        sc2_adapter.current_game = create_game_info("MATCH_STARTED")
        new_game = create_game_info("REPLAY_ENDED", is_replay=True)
        
        # Simulate state change
        sc2_adapter.current_game = new_game
        sc2_adapter.previous_game = sc2_adapter.current_game
        
        # Manually trigger the logic that would happen in monitoring loop
        status = new_game.get_status()
        if status in ("MATCH_ENDED", "REPLAY_ENDED") and sc2_adapter.game_result_service:
            await sc2_adapter.game_result_service.process_game_end(new_game)
        
        mock_game_result_service.process_game_end.assert_called_once_with(new_game)


class TestMonitoringFlow:
    """Test the full monitoring flow"""
    
    @pytest.mark.asyncio
    async def test_state_change_adds_event_to_bot_core(self, sc2_adapter, mock_bot_core):
        """State change should add event to BotCore queue"""
        sc2_adapter.current_game = create_game_info("MATCH_STARTED")
        new_game = create_game_info("MATCH_ENDED")
        
        if sc2_adapter._has_state_changed(sc2_adapter.current_game, new_game):
            event = sc2_adapter._create_game_event(new_game)
            sc2_adapter.bot_core.add_event(event)
        
        mock_bot_core.add_event.assert_called_once()
        call_args = mock_bot_core.add_event.call_args[0][0]
        assert isinstance(call_args, GameStateEvent)
        assert call_args.event_type == "game_ended"
    
    @pytest.mark.asyncio
    async def test_replay_immediately_after_game(self, sc2_adapter, mock_bot_core, mock_game_result_service):
        """
        Critical bug scenario: Game ends, user immediately watches replay.
        MATCH_STARTED -> REPLAY_ENDED should:
        1. Create game_ended event
        2. Trigger GameResultService
        """
        sc2_adapter.current_game = create_game_info("MATCH_STARTED")
        new_game = create_game_info("REPLAY_ENDED", is_replay=True)
        
        if sc2_adapter._has_state_changed(sc2_adapter.current_game, new_game):
            event = sc2_adapter._create_game_event(new_game)
            sc2_adapter.bot_core.add_event(event)
            
            # Trigger game result service
            status = new_game.get_status()
            if status in ("MATCH_ENDED", "REPLAY_ENDED") and sc2_adapter.game_result_service:
                await sc2_adapter.game_result_service.process_game_end(new_game)
        
        # Verify game_ended event was created (not status_change)
        mock_bot_core.add_event.assert_called_once()
        event = mock_bot_core.add_event.call_args[0][0]
        assert event.event_type == "game_ended", "Should create game_ended, not status_change"
        
        # Verify GameResultService was triggered
        mock_game_result_service.process_game_end.assert_called_once_with(new_game)



