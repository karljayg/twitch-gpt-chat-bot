import logging
from core.command_service import ICommandHandler, CommandContext
import settings.config as config

logger = logging.getLogger(__name__)

class RetryProcessingHandler(ICommandHandler):
    """Handler for 'please retry' command - retries failed game processing"""
    def __init__(self, game_result_service):
        self.game_result_service = game_result_service
        
    async def handle(self, context: CommandContext, args: str):
        # Only allow broadcaster to retry
        if context.author.lower() != config.PAGE.lower():
            logger.info(f"Retry command rejected - not from broadcaster (from: {context.author})")
            return
        
        try:
            success = await self.game_result_service.retry_last_game()
            if not success:
                await context.chat_service.send_message(
                    context.channel,
                    "Retry failed - no recent replay found or processing error. Check logs for details."
                )
        except Exception as e:
            logger.error(f"Error during retry processing: {e}", exc_info=True)
            await context.chat_service.send_message(
                context.channel, 
                f"Retry failed: {e}. You can try again with 'please retry'"
            )

