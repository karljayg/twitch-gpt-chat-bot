import logging
from core.command_service import ICommandHandler, CommandContext
from api.fsl_integration import FSLIntegration
from settings import config

logger = logging.getLogger(__name__)

class FSLHandler(ICommandHandler):
    """Handler for !fsl_review command to generate FSL reviewer links"""
    def __init__(self):
        if getattr(config, 'ENABLE_FSL_INTEGRATION', False):
            self.fsl_integration = FSLIntegration(
                api_url=config.FSL_API_URL,
                api_token=config.FSL_API_TOKEN,
                reviewer_weight=config.FSL_REVIEWER_WEIGHT
            )
        else:
            self.fsl_integration = None
        
    async def handle(self, context: CommandContext, args: str):
        if not self.fsl_integration:
            await context.chat_service.send_message(context.channel, "FSL integration is disabled.")
            return

        # Target user defaults to the sender
        target_user = context.author
        
        # If args provided (e.g. "!fsl_review otheruser"), use that
        # But usually users generate their own links. 
        if args:
            # Remove @ if present
            target_user = args.strip().lstrip('@')
            
        logger.info(f"Handling FSL review link request for: {target_user}")
        
        link = self.fsl_integration.get_reviewer_link(target_user)
        
        if link:
            # Send the link as a whisper (private message) to the user
            if hasattr(context.chat_service, 'send_whisper'):
                await context.chat_service.send_whisper(target_user, f"FSL Review Link: {link}")
            else:
                # Fallback to public message if whisper not available
                await context.chat_service.send_message(context.channel, f"FSL Review Link for {target_user}: {link}")
        else:
            # Send error as whisper too
            if hasattr(context.chat_service, 'send_whisper'):
                await context.chat_service.send_whisper(target_user, f"Could not retrieve FSL link. (API Error or User already exists without link access)")
            else:
                await context.chat_service.send_message(context.channel, f"Could not retrieve FSL link for {target_user}. (API Error or User already exists without link access)")


