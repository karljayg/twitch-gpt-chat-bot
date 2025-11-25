import pytest
from unittest.mock import MagicMock, AsyncMock, patch
# We'll create the handler next
# from core.handlers.wiki_handler import WikiHandler
from core.command_service import CommandContext
from core.interfaces import ILanguageModel

# Placeholder
class WikiHandler:
    def __init__(self, llm):
        self.llm = llm
    async def handle(self, context, args):
        pass

@pytest.fixture
def mock_llm():
    llm = MagicMock(spec=ILanguageModel)
    llm.generate_response = AsyncMock(return_value="AI Summary: Zerg Rush is fast.")
    return llm

@pytest.fixture
def mock_chat_service():
    service = MagicMock()
    service.send_message = AsyncMock()
    return service

@pytest.mark.asyncio
async def test_wiki_handler_success(mock_llm, mock_chat_service):
    # Import real handler once created
    from core.handlers.wiki_handler import WikiHandler
    
    handler = WikiHandler(mock_llm)
    context = CommandContext("wiki zerglings", "channel1", "user1", "twitch", mock_chat_service)
    
    # Mock wikipedia_question (which is blocking I/O)
    with patch('utils.wiki_utils.wikipedia_question', return_value="Raw Wiki Data") as mock_wiki:
        await handler.handle(context, "zerglings")
        
        # Verify wiki call
        mock_wiki.assert_called_with("zerglings", None)
        
        # Verify LLM call
        mock_llm.generate_response.assert_called()
        
        # Verify chat response
        mock_chat_service.send_message.assert_called_with("channel1", "AI Summary: Zerg Rush is fast.")

@pytest.mark.asyncio
async def test_wiki_handler_no_args(mock_llm, mock_chat_service):
    from core.handlers.wiki_handler import WikiHandler
    
    handler = WikiHandler(mock_llm)
    context = CommandContext("wiki", "channel1", "user1", "twitch", mock_chat_service)
    
    await handler.handle(context, "")
    
    mock_chat_service.send_message.assert_called_with("channel1", "Usage: !wiki <topic>")

