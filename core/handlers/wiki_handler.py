import logging
import asyncio
from core.command_service import ICommandHandler, CommandContext
from core.interfaces import ILanguageModel
import utils.wiki_utils

logger = logging.getLogger(__name__)

class WikiHandler(ICommandHandler):
    """Handler for !wiki commands"""
    def __init__(self, llm: ILanguageModel):
        self.llm = llm
        
    async def handle(self, context: CommandContext, args: str):
        if not args:
            await context.chat_service.send_message(context.channel, "Usage: !wiki <topic>")
            return

        logger.info(f"Handling wiki request for: {args}")
        
        loop = asyncio.get_running_loop()
        try:
            # Run legacy synchronous code in executor
            # utils.wiki_utils.wikipedia_question(question, self)
            # We pass None for self because it's unused in the legacy function
            wiki_result = await loop.run_in_executor(
                None,
                utils.wiki_utils.wikipedia_question,
                args,
                None
            )
            
            # Prepare response using LLM to match bot personality
            prompt = f"Based on this info: '{wiki_result}', give a short summary for Twitch chat (under 450 chars)."
            
            response = await self.llm.generate_response(prompt)
            
            # Send response
            await context.chat_service.send_message(context.channel, response)
            
        except Exception as e:
            logger.error(f"Wiki handler error: {e}")
            await context.chat_service.send_message(context.channel, "Could not retrieve wiki info.")


