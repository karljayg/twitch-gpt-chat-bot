from abc import ABC, abstractmethod
from typing import Any, List, Optional, Dict

class IChatService(ABC):
    """Interface for chat platforms (Twitch, Discord)"""
    
    @abstractmethod
    async def send_message(self, channel: str, message: str) -> None:
        """Send a message to the specified channel"""
        pass
    
    @abstractmethod
    def get_platform_name(self) -> str:
        """Return the name of the platform (e.g. 'twitch', 'discord')"""
        pass

class IGameStateProvider(ABC):
    """Interface for game state providers (SC2 API)"""
    
    @abstractmethod
    def get_current_game_state(self) -> Any:
        """Return the current state of the game"""
        pass
    
    @abstractmethod
    def get_last_game_result(self) -> Any:
        """Return result of the last completed game"""
        pass

class ILanguageModel(ABC):
    """Interface for LLM providers (OpenAI)"""
    
    @abstractmethod
    async def generate_response(self, prompt: str, context: List[str] = None) -> str:
        """Generate a response based on prompt and context (with persona)"""
        pass

    @abstractmethod
    async def generate_raw(self, prompt: str) -> str:
        """Generate a raw response without persona/system prompt injection"""
        pass

class IReplayRepository(ABC):
    """Interface for replay data access"""
    @abstractmethod
    async def get_latest_replay(self) -> Optional[dict]:
        pass
    
    @abstractmethod
    async def save_replay(self, replay_data: Any) -> bool:
        pass
    
    @abstractmethod
    async def update_comment(self, comment: str) -> bool:
        pass

class IPlayerRepository(ABC):
    """Interface for player data access"""
    @abstractmethod
    async def get_player_stats(self, player_name: str) -> Optional[str]:
        pass
    
    @abstractmethod
    async def get_matchup_stats(self, player_name: str) -> Optional[str]:
        pass
        
    @abstractmethod
    async def get_player_records(self, player_name: str) -> List[str]:
        """Get history of games against a player"""
        pass

class IAudioService(ABC):
    """Interface for audio output (TTS and Sound Effects)"""
    @abstractmethod
    async def speak(self, text: str) -> None:
        """Convert text to speech"""
        pass
        
    @abstractmethod
    async def play_sound(self, sound_key: str) -> None:
        """Play a sound effect by key"""
        pass

class IDatabaseClient(ABC):
    """
    Interface for database operations.
    Implementations can use direct MySQL (LocalDatabaseClient) or REST API (ApiDatabaseClient).
    """
    
    # ===== Player Operations =====
    
    @abstractmethod
    def check_player_and_race_exists(self, player_name: str, player_race: str) -> Optional[Dict]:
        """Check if player exists with specific race, return last game data"""
        pass
    
    @abstractmethod
    def check_player_exists(self, player_name: str) -> Optional[Dict]:
        """Check if player exists, return player data"""
        pass
    
    @abstractmethod
    def get_player_records(self, player_name: str) -> List[str]:
        """Get player's win/loss records against opponents"""
        pass
    
    @abstractmethod
    def get_player_comments(self, player_name: str, player_race: str) -> List[Dict]:
        """Get all games with player comments for specific player and race"""
        pass
    
    @abstractmethod
    def get_player_overall_records(self, player_name: str) -> str:
        """Get overall win/loss records for player"""
        pass
    
    # ===== Replay Operations =====
    
    @abstractmethod
    def get_last_replay_info(self) -> Optional[Dict]:
        """Get the most recent replay"""
        pass
    
    @abstractmethod
    def get_replay_by_id(self, replay_id: int) -> Optional[Dict]:
        """Get specific replay by ID"""
        pass
    
    @abstractmethod
    def extract_opponent_build_order(self, opponent_name: str, opp_race: str, 
                                     streamer_picked_race: str) -> Optional[List[str]]:
        """Extract opponent's build order from replay summary"""
        pass
    
    # ===== Connection Management =====
    
    @abstractmethod
    def ensure_connection(self):
        """Ensure connection is alive (for MySQL) or verify API is reachable"""
        pass
    
    @abstractmethod
    def keep_connection_alive(self):
        """Keep connection alive (MySQL heartbeat) or no-op for API"""
        pass
    
    # ===== Legacy Compatibility =====
    
    @property
    @abstractmethod
    def cursor(self):
        """Database cursor (for legacy code compatibility)"""
        pass
    
    @property
    @abstractmethod
    def connection(self):
        """Database connection (for legacy code compatibility)"""
        pass
    
    @property
    @abstractmethod
    def logger(self):
        """Logger instance"""
        pass
