import logging
from core.command_service import ICommandHandler, CommandContext
from core.interfaces import IPlayerRepository, ILanguageModel

logger = logging.getLogger(__name__)

class HistoryHandler(ICommandHandler):
    """Handler for !history commands"""
    def __init__(self, player_repo: IPlayerRepository, llm: ILanguageModel):
        self.player_repo = player_repo
        self.llm = llm
        
    async def handle(self, context: CommandContext, args: str):
        if not args:
            await context.chat_service.send_message(context.channel, "Usage: !history <player>")
            return
            
        player_name = args.strip()
        logger.info(f"Handling history request for: {player_name}")
        
        try:
            history_list = await self.player_repo.get_player_records(player_name)
            
            if not history_list:
                prompt = f"restate all of the info here: there are no game records in history for {player_name}"
            else:
                # Legacy Logic Port: Exact Formatting
                # Process each record and format it as desired
                # Record format from DB is usually: "Player1 vs Player2, X wins - Y losses"
                # Legacy logic splits this manually, but we can trust the DB output or reformat if needed.
                # Legacy code: f"{rec.split(', ')[0]} vs {rec.split(', ')[1]}, {rec.split(', ')[2].split(' ')[0]}-{rec.split(', ')[3].split(' ')[0]}"
                
                formatted_records = []
                for rec in history_list:
                    try:
                        # Attempt legacy splitting to match exact format "P1 vs P2, 1-0"
                        parts = rec.split(', ')
                        if len(parts) >= 4:
                            p1 = parts[0]
                            p2 = parts[1]
                            wins = parts[2].split(' ')[0]
                            losses = parts[3].split(' ')[0]
                            formatted_records.append(f"{p1} vs {p2}, {wins}-{losses}")
                        else:
                            formatted_records.append(rec)
                    except:
                        formatted_records.append(rec)

                result_string = " and ".join(formatted_records)
                
                import utils.tokensArray as tokensArray
                from settings import config
                trimmed_msg = tokensArray.truncate_to_byte_limit(result_string, config.TWITCH_CHAT_BYTE_LIMIT)
                    
                prompt = f"restate all of the info here and do not exclude anything: total win/loss record of {player_name} we know the results of so far {trimmed_msg}"
            
            # Use generate_response (Injects Persona/Mood - Matching legacy processMessageForOpenAI)
            response = await self.llm.generate_response(prompt)
            await context.chat_service.send_message(context.channel, response)
            
        except Exception as e:
            logger.error(f"Error in history handler: {e}")
            await context.chat_service.send_message(context.channel, "Error retrieving history.")


