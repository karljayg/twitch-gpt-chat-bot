import asyncio
from typing import List, Optional
from core.interfaces import IChatService, IGameStateProvider, ILanguageModel
from core.events import BaseEvent, MessageEvent, GameStateEvent

class MockChatService(IChatService):
    def __init__(self, platform_name="mock_chat"):
        self.platform_name = platform_name
        self.sent_messages = []

    async def send_message(self, channel: str, message: str) -> None:
        self.sent_messages.append({"channel": channel, "message": message})

    def get_platform_name(self) -> str:
        return self.platform_name

class MockGameStateProvider(IGameStateProvider):
    def __init__(self):
        self.current_state = None
        self.last_result = None

    def get_current_game_state(self):
        return self.current_state

    def get_last_game_result(self):
        return self.last_result
        
    def set_mock_state(self, state):
        self.current_state = state

class MockLanguageModel(ILanguageModel):
    def __init__(self):
        self.responses = {}
        self.default_response = "I am a mock AI."

    async def generate_response(self, prompt: str, context: List[str] = None) -> str:
        for key, response in self.responses.items():
            if key in prompt:
                return response
        return self.default_response

    async def generate_raw(self, prompt: str) -> str:
        """Mock implementation of generate_raw"""
        for key, response in self.responses.items():
            if key in prompt:
                return response
        return self.default_response
        
    def set_response(self, trigger: str, response: str):
        self.responses[trigger] = response


