import logging
from core.command_service import ICommandHandler, CommandContext
from core.interfaces import ILanguageModel, IPlayerRepository

logger = logging.getLogger(__name__)

class CareerHandler(ICommandHandler):
    """Handler for !career commands"""
    def __init__(self, player_repo: IPlayerRepository, llm: ILanguageModel):
        self.player_repo = player_repo
        self.llm = llm
        
    async def handle(self, context: CommandContext, args: str):
        if not args:
            await context.chat_service.send_message(context.channel, "Usage: !career <player>")
            return
            
        player_name = args.strip()
        logger.info(f"Handling career request for: {player_name}")
        
        try:
            # Repository handles async access
            overall = await self.player_repo.get_player_stats(player_name)
            matchups = await self.player_repo.get_matchup_stats(player_name)
            
            career_record = ""
            if overall:
                career_record += overall
            if matchups:
                career_record += " " + matchups
            
            if career_record:
                # Legacy Logic Port: Exact Prompt Engineering
                import utils.tokensArray as tokensArray
                from settings import config
                
                trimmed_msg = tokensArray.truncate_to_byte_limit(career_record, config.TWITCH_CHAT_BYTE_LIMIT)
                
                prompt = f'''
                Review this example:

                    when given a player, DarkMenace the career records are:

                        Overall matchup records for darkmenace: 425 wins - 394 losses Race matchup records for darkmenace: Protoss vs Protoss: 15 wins - 51 lossesProtoss vs Terran: 11 wins - 8 lossesProtoss vs Zerg: 1 wins - 1 lossesTerran vs Protoss: 8 wins - 35 lossesTerran vs Terran: 3 wins - 1 lossesTerran vs Zerg: 4 wins - 3 lossesZerg vs Protoss: 170 wins - 137 lossesZerg vs Terran: 138 wins - 100 lossesZerg vs Zerg: 75 wins - 58 losses

                    From the above, say it exactly like this format:

                        overall: 425-394, each matchup: PvP: 15-51 PvT: 11-8 PvZ: 1-1 TvP: 8-35 TvT: 3-1 TvZ: 4-3 ZvP: 170-137 ZvT: 138-100 ZvZ: 75-58. Strong Zerg performance with balanced racial distribution.

                Now do the same but only using this data:

                    {player_name} : {trimmed_msg}.

                Include a period and space before your 10 word comment.
                '''
                
                # Use generate_raw to bypass persona/mood injection (matching legacy send_prompt_to_openai)
                response = await self.llm.generate_raw(prompt)
            else:
                prompt = f"Restate all of the info here: There is no career games that I know for {player_name} ."
                # For empty results, legacy used processMessageForOpenAI (persona injected) but raw prompt is safer for consistency here
                # We'll stick to generate_response for the "no records" case to keep it friendly? 
                # Actually legacy used send_prompt_to_openai for the stats path, but the NO stats path is just a simple message.
                # Let's use generate_response for the friendly "no records" message.
                response = await self.llm.generate_response(prompt)

            if response:
                await context.chat_service.send_message(context.channel, response)
            
        except Exception as e:
            logger.error(f"Career handler error: {e}")
            await context.chat_service.send_message(context.channel, "Error retrieving career stats.")
