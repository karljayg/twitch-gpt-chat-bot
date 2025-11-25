import logging
import re
from core.command_service import ICommandHandler, CommandContext
from core.interfaces import ILanguageModel, IChatService
from core.repositories.sql_player_repository import SqlPlayerRepository
import settings.config as config
import utils.tokensArray as tokensArray

logger = logging.getLogger(__name__)

class HeadToHeadHandler(ICommandHandler):
    """Handler for 'head to head' commands"""
    def __init__(self, player_repo: SqlPlayerRepository, llm: ILanguageModel):
        self.player_repo = player_repo
        self.llm = llm
        
    async def handle(self, context: CommandContext, args: str):
        # args might be empty if the command was matched as a substring of a larger sentence
        # We need to parse the full message to extract names if they aren't in args
        
        message_content = context.message
        logger.debug(f"Handling head to head request: {message_content}")

        # Use regex to extract player names: "head to head <player1> <player2>"
        match = re.search(r"head to head (\w+) (\w+)", message_content, re.IGNORECASE)
        if not match:
            await context.chat_service.send_message(context.channel, "Usage: head to head <player1> <player2>")
            return

        player1_name, player2_name = match.groups()
        
        try:
            # We need to access the underlying DB method directly or add this to the repository interface
            # Since IPlayerRepository is abstract, we should ideally add it there.
            # For now, we'll assume SqlPlayerRepository has access to the DB method or we add a specific method to it.
            
            # Check if the repository has the specific method, if not we might need to extend it
            # or access the db directly if exposed (less ideal but pragmatic for migration)
            if hasattr(self.player_repo, 'db') and hasattr(self.player_repo.db, 'get_head_to_head_matchup'):
                 # Run in executor because DB calls are synchronous
                import asyncio
                loop = asyncio.get_running_loop()
                head_to_head_list = await loop.run_in_executor(
                    None, 
                    self.player_repo.db.get_head_to_head_matchup, 
                    player1_name, 
                    player2_name
                )
            else:
                logger.error("Player repository does not support head to head lookup")
                await context.chat_service.send_message(context.channel, "Error: Feature not supported by current repository.")
                return

            if head_to_head_list:
                result_string = ", ".join(head_to_head_list)
                trimmed_result = tokensArray.truncate_to_byte_limit(result_string, config.TWITCH_CHAT_BYTE_LIMIT)

                prompt = f'''
                    Review this example:

                        when given 2 player, DarkMenace vs KJ the records are:

                            ['DarkMenace (Terran) vs KJ (Zerg), 29 wins - 7 wins', 'DarkMenace (Protoss) vs KJ (Zerg), 9 wins - 12 wins', 'DarkMenace (Zerg) vs KJ (Zerg), 3 wins - 2 wins', 'DarkMenace (Protoss) vs KJ (Terran), 6 wins - 1 wins', 'DarkMenace (Terran) vs KJ (Terran), 1 wins - 0 wins', 'DarkMenace (Protoss) vs KJ (Protoss), 2 wins - 2 wins']

                        From the above, say it exactly like this format:

                            overall: 50-24, each matchup: TvZ 29-7, PvZ 9-12, ZvZ 3-2, PvT 6-1, TvT 1-0, PvP 2-2. DarkMenace dominates with Terran against Zerg matchups consistently.

                    Now do the same but only using this data:

                        {player1_name} vs {player2_name}: {trimmed_result}.

                    Include a period and space before your 10 word comment.
                '''
                
                # Use generate_raw to bypass persona/mood injection (matching legacy send_prompt_to_openai)
                response = await self.llm.generate_raw(prompt)
                
                # CRITICAL FIX: Discord messages are tracked by legacy bot.
                # If we just 'return' from the handler, the legacy bot tracks it but sees no response.
                # We must explicitly send the response here.
                await context.chat_service.send_message(context.channel, response)
                
            else:
                msg = f"Restate all of the info here: There are no head-to-head game records between {player1_name} and {player2_name} ."
                response = await self.llm.generate_response(msg)
                await context.chat_service.send_message(context.channel, response)

        except Exception as e:
            logger.error(f"Error in head to head handler: {e}")
            await context.chat_service.send_message(context.channel, "An error occurred while retrieving head to head stats.")
