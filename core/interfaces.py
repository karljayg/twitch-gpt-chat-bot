from abc import ABC, abstractmethod
from typing import Any, List, Optional

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
