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
            logger.info("Retry command rejected - not from broadcaster (from: %s)", context.author)
            return
        
        try:
            parsed_ref = None
            args = (args or "").strip()
            if args:
                try:
                    parsed_ref = int(args)
                except ValueError:
                    await context.chat_service.send_message(
                        context.channel,
                        "Usage: please retry [ReplayID|-N]. Examples: 'please retry', 'please retry 24943', 'please retry -3'",
                    )
                    return

            success, detail = await self.game_result_service.retry_with_reference(parsed_ref)
            if not success:
                await context.chat_service.send_message(
                    context.channel,
                    f"Retry failed - {detail}"
                )
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error during retry processing: %s", e, exc_info=True)
            await context.chat_service.send_message(
                context.channel, 
                f"Retry failed: {e}. You can try again with 'please retry', 'please retry <ReplayID>', or 'please retry -3'"
            )

