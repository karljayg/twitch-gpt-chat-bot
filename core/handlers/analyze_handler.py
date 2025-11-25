import logging
from core.command_service import ICommandHandler, CommandContext

logger = logging.getLogger(__name__)

class AnalyzeHandler(ICommandHandler):
    """Handler for !analyze commands"""
    def __init__(self, analysis_service):
        self.analysis_service = analysis_service
        
    async def handle(self, context: CommandContext, args: str):
        if not args:
            await context.chat_service.send_message(context.channel, "Usage: !analyze <player> [race]")
            return
            
        parts = args.split()
        player_name = parts[0]
        player_race = parts[1] if len(parts) > 1 else "Unknown"
        
        logger.info(f"Analyzing opponent: {player_name} ({player_race})")
        
        try:
            result = await self.analysis_service.analyze_opponent(player_name, player_race)
            
            if not result:
                await context.chat_service.send_message(context.channel, f"Could not analyze opponent {player_name}.")
                return
                
            # Basic formatting of the analysis result
            # Ideally we would use a specialized formatter or LLM here
            msg = f"Analysis for {player_name}: "
            if isinstance(result, dict):
                items = [f"{k}: {v}" for k, v in result.items() if k in ['play_style', 'win_rate', 'main_race', 'notes']]
                msg += ", ".join(items)
            else:
                msg += str(result)
                
            await context.chat_service.send_message(context.channel, msg)
            
        except Exception as e:
            logger.error(f"Error in analyze handler: {e}")
            await context.chat_service.send_message(context.channel, "Error processing analysis.")


