import logging
from core.command_service import ICommandHandler, CommandContext
import settings.config as config

logger = logging.getLogger(__name__)

class ReplayTestHandler(ICommandHandler):
    """Handler for 'please replay <id>' command - tests strategy summary against historical replay"""
    def __init__(self, game_result_service):
        self.game_result_service = game_result_service
        
    async def handle(self, context: CommandContext, args: str):
        # Only allow broadcaster to test
        if context.author.lower() != config.PAGE.lower():
            logger.info(f"Replay test command rejected - not from broadcaster (from: {context.author})")
            return
        
        # Parse replay ID from args
        args = args.strip()
        if not args:
            await context.chat_service.send_message(
                context.channel,
                "Usage: please replay <replayID> - e.g. 'please replay 12345'"
            )
            return
        
        try:
            replay_id = int(args)
        except ValueError:
            await context.chat_service.send_message(
                context.channel,
                f"Invalid replay ID: '{args}'. Must be a number."
            )
            return
        
        try:
            result = await self.game_result_service.test_replay_by_id(replay_id)
            await context.chat_service.send_message(context.channel, result)
        except Exception as e:
            logger.error(f"Error during replay test: {e}", exc_info=True)
            await context.chat_service.send_message(
                context.channel, 
                f"Replay test failed: {e}"
            )

