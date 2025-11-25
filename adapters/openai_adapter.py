import logging
from typing import List, Optional
from core.interfaces import ILanguageModel
import api.chat_utils as chat_utils
import settings.config as config

logger = logging.getLogger(__name__)

class OpenAIAdapter(ILanguageModel):
    def __init__(self):
        self.logger = logger
        
    async def generate_response(self, prompt: str, context: List[str] = None) -> str:
        """
        Generates a response using the existing chat_utils logic (with persona).
        """
        try:
            from api.chat_utils import process_ai_message
            
            response = process_ai_message(
                user_message=prompt,
                conversation_mode="normal", # Default
                contextHistory=context if context else [],
                platform="core",
                logger=self.logger
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error in OpenAIAdapter.generate_response: {e}")
            return "I'm having trouble thinking right now."

    async def generate_raw(self, prompt: str) -> str:
        """
        Generates a raw response directly from OpenAI without persona injection.
        Useful for system tasks like JSON parsing, summarization, etc.
        """
        try:
            from api.chat_utils import send_prompt_to_openai
            
            completion = send_prompt_to_openai(prompt)
            
            if completion and completion.choices and completion.choices[0].message:
                return completion.choices[0].message.content
            
            return ""
            
        except Exception as e:
            logger.error(f"Error in OpenAIAdapter.generate_raw: {e}")
            return ""


