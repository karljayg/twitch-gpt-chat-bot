import abc
import logging
from typing import List, Any, Dict, Optional

logger = logging.getLogger(__name__)

class CommandContext:
    """Context object passed to command handlers"""
    def __init__(self, message: str, channel: str, author: str, platform: str, chat_service: Any):
        self.message = message
        self.channel = channel
        self.author = author
        self.platform = platform
        self.chat_service = chat_service

class ICommandHandler(abc.ABC):
    """Interface for command handlers"""
    @abc.abstractmethod
    async def handle(self, context: CommandContext, args: str):
        pass

class CommandService:
    """Service for parsing and dispatching chat commands"""
    def __init__(self, chat_services: List[Any]):
        self.chat_services = chat_services
        self.handlers: Dict[str, ICommandHandler] = {}
        
    def register_handler(self, keyword: str, handler: ICommandHandler):
        """Register a handler for a command keyword (case-insensitive)"""
        self.handlers[keyword.lower()] = handler
        logger.info(f"Registered command handler: '{keyword.lower()}'")
        
    async def handle_message(self, message: str, channel: str, author: str, platform: str) -> bool:
        """
        Process a message and dispatch to handler if it matches a command.
        Returns True if a command was handled, False otherwise.
        """
        if not message:
            return False
            
        msg_lower = message.lower()
        logger.debug(f"Checking command for: '{msg_lower}' (registered: {list(self.handlers.keys())})")
        
        # Sort handlers by length (descending) to match longest prefix first
        # IMPORTANT: Use strict matching for multi-word commands to avoid partial matches in normal sentences
        sorted_keys = sorted(self.handlers.keys(), key=len, reverse=True)
        
        for keyword in sorted_keys:
            is_match = False
            args = ""
            
            # 1. Exact match
            if msg_lower == keyword:
                is_match = True
                args = ""
            # 2. Exact match with prefix
            elif msg_lower == "!" + keyword:
                is_match = True
                args = ""
            # 3. Starts with keyword followed by space (standard command)
            elif msg_lower.startswith(keyword + " "):
                is_match = True
                args = message[len(keyword):].strip()
            # 4. Starts with prefix followed by space
            elif msg_lower.startswith("!" + keyword + " "):
                is_match = True
                args = message[len(keyword)+1:].strip()
            # 5. Contains keyword for special natural language commands (like "player comment")
            #    BUT be careful not to over-match common words.
            #    "head to head" is safe to search anywhere.
            elif keyword in ["head to head", "player comment"] and keyword in msg_lower:
                is_match = True
                args = message # Pass full message for substring commands to parse internally
                
            if is_match:
                logger.info(f"Command match: '{keyword}' from {author}")
                
                # Find the correct chat service for this platform
                service = self._get_chat_service(platform)
                
                context = CommandContext(message, channel, author, platform, service)
                
                try:
                    await self.handlers[keyword].handle(context, args)
                    return True
                except Exception as e:
                    logger.error(f"Error handling command '{keyword}': {e}")
                    return True # Still return True because we matched a command intent
                    
        return False

    def _get_chat_service(self, platform: str) -> Optional[Any]:
        """Helper to find the right chat service"""
        if not self.chat_services:
            return None
            
        for service in self.chat_services:
            if hasattr(service, 'platform') and service.platform == platform:
                return service
        
        # Fallback to first service if generic or only one
        return self.chat_services[0]
