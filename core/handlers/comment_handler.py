import logging
import asyncio
import json
import os
from core.command_service import ICommandHandler, CommandContext
from core.interfaces import IReplayRepository
from settings import config

logger = logging.getLogger(__name__)

class CommentHandler(ICommandHandler):
    """Handler for 'player comment' commands"""
    def __init__(self, replay_repo: IReplayRepository, pattern_learner):
        self.replay_repo = replay_repo
        self.pattern_learner = pattern_learner
        
    async def handle(self, context: CommandContext, args: str):
        comment_text = args.strip()
        if not comment_text:
            await context.chat_service.send_message(context.channel, "Please provide comment text after 'player comment'")
            return
        
        # Check if there's an active pattern learning context from the legacy system
        # If so, we need to process this as a natural language response to the suggestions
        twitch_bot = None
        if hasattr(context.chat_service, 'twitch_bot'):
            twitch_bot = context.chat_service.twitch_bot
        
        if twitch_bot and hasattr(twitch_bot, 'pattern_learning_context') and twitch_bot.pattern_learning_context:
            # Check if context is still fresh (within 5 minutes)
            import time
            context_age = time.time() - twitch_bot.pattern_learning_context.get('timestamp', 0)
            
            if context_age <= 300:  # 5 minutes
                logger.info(f"Pattern learning context active (age: {context_age/60:.1f} min) - processing as NLP response")
                
                # Check if we're awaiting clarification from previous "yes" response
                if twitch_bot.pattern_learning_context.get('awaiting_clarification', False):
                    # User is responding to clarification question
                    response_lower = comment_text.strip().lower()
                    if response_lower in ['y', 'yes', 'yeah']:
                        # User confirmed first option (pattern match)
                        comment_text = twitch_bot.pattern_learning_context.get('pattern_match', comment_text)
                        logger.info(f"User confirmed pattern match: {comment_text}")
                        twitch_bot.pattern_learning_context['awaiting_clarification'] = False
                    elif response_lower in ['n', 'no', 'nope']:
                        # User wants second option (AI summary)
                        comment_text = twitch_bot.pattern_learning_context.get('ai_summary', comment_text)
                        logger.info(f"User chose AI summary: {comment_text}")
                        twitch_bot.pattern_learning_context['awaiting_clarification'] = False
                    else:
                        # Not a clear Y/N response, treat as custom
                        logger.info(f"User provided custom response during clarification: {comment_text}")
                        twitch_bot.pattern_learning_context['awaiting_clarification'] = False
                else:
                    # Process through legacy NLP system
                    loop = asyncio.get_running_loop()
                    try:
                        action, interpreted_comment = await loop.run_in_executor(
                            None,
                            twitch_bot._process_natural_language_pattern_response,
                            comment_text,
                            logger
                        )
                        
                        logger.debug(f"NLP interpretation: action={action}, comment={interpreted_comment}")
                        
                        # If NLP extracted a custom comment, use that instead of raw text
                        if action == 'ask_clarification':
                            # User said "yes" without specifying - ask for clarification
                            pattern_match = twitch_bot.pattern_learning_context.get('pattern_match', 'pattern match')
                            await context.chat_service.send_message(
                                context.channel, 
                                f"I think you want the first one ('{pattern_match}'), Y/N?"
                            )
                            # Set clarification flag in context
                            twitch_bot.pattern_learning_context['awaiting_clarification'] = True
                            return  # Wait for next response
                        elif action == 'custom' and interpreted_comment:
                            comment_text = interpreted_comment
                            logger.info(f"Using NLP-extracted comment: {comment_text}")
                        elif action == 'use_pattern':
                            comment_text = twitch_bot.pattern_learning_context.get('pattern_match', comment_text)
                            logger.info(f"Using pattern match comment: {comment_text}")
                        elif action == 'use_ai_summary':
                            comment_text = twitch_bot.pattern_learning_context.get('ai_summary', comment_text)
                            logger.info(f"Using AI summary comment: {comment_text}")
                        elif action == 'skip':
                            await context.chat_service.send_message(context.channel, "Skipping - no comment saved.")
                            twitch_bot.pattern_learning_context = None  # Clear context
                            return
                        
                        # Clear the context after processing
                        twitch_bot.pattern_learning_context = None
                    
                    except Exception as e:
                        logger.error(f"Error processing NLP response: {e}")
                        # Fall through to save raw comment
            else:
                logger.info(f"Pattern learning context is stale (age: {context_age/60:.1f} min) - treating as direct comment")
                twitch_bot.pattern_learning_context = None  # Clear stale context
            
        # Get latest replay
        try:
            # Repo handles async/executor logic
            latest_replay = await self.replay_repo.get_latest_replay()
            
            if not latest_replay:
                await context.chat_service.send_message(context.channel, "No replays found in database - please play a game first")
                return
                
            opponent = latest_replay.get('opponent', 'Unknown')
            map_name = latest_replay.get('map', 'Unknown')
            game_date = latest_replay.get('date', 'Unknown')
            existing_comment = latest_replay.get('existing_comment')
            
            # Check if comment already exists - ask for confirmation before overwriting
            if existing_comment:
                # Store pending state for Y/N confirmation in legacy bot
                if twitch_bot:
                    twitch_bot.pending_player_comment = {
                        'comment': comment_text,
                        'replay': latest_replay,
                        'timestamp': latest_replay.get('timestamp', 0)
                    }
                
                response = f"There is already data there for last game vs {opponent} on {map_name} ({game_date}). Are you sure you want to overwrite it? Y/N"
                await context.chat_service.send_message(context.channel, response)
                logger.info(f"Existing comment found, asking for overwrite confirmation")
                return
            
            # No existing comment - save directly
            # Update DB
            success = await self.replay_repo.update_comment(comment_text)
            
            if success:
                # Update Pattern Learner (Legacy component, likely sync)
                # We still need to run this in executor if it does file I/O
                if self.pattern_learner:
                    loop = asyncio.get_running_loop()
                    game_data = {
                        'opponent_name': opponent,
                        'map': map_name,
                        'date': game_date,
                        'result': latest_replay.get('result', 'Unknown'),
                        'duration': latest_replay.get('duration', 'Unknown')
                    }
                    
                    # Get build_order from last replay JSON (saved after each game)
                    try:
                        replay_json_path = config.LAST_REPLAY_JSON_FILE
                        if os.path.exists(replay_json_path):
                            with open(replay_json_path, 'r') as f:
                                replay_data = json.load(f)
                            
                            # Find opponent's build order
                            player_accounts_lower = [name.lower() for name in config.SC2_PLAYER_ACCOUNTS]
                            for p_key, p_data in replay_data.get('players', {}).items():
                                if p_data.get('name', '').lower() not in player_accounts_lower:
                                    game_data['build_order'] = p_data.get('buildOrder', [])
                                    game_data['opponent_race'] = p_data.get('race', 'Unknown')
                                    logger.info(f"Loaded {len(game_data['build_order'])} build order steps from last replay")
                                    break
                    except Exception as e:
                        logger.warning(f"Could not load build order from replay JSON: {e}")
                    
                    await loop.run_in_executor(
                        None,
                        self.pattern_learner._process_new_comment,
                        game_data,
                        comment_text
                    )
                    await loop.run_in_executor(None, self.pattern_learner.save_patterns_to_file)
                    
                response = f"Saved comment for game vs {opponent} on {map_name} ({game_date}): '{comment_text}'"
                await context.chat_service.send_message(context.channel, response)
            else:
                await context.chat_service.send_message(context.channel, f"Failed to save comment to database for {opponent}")
                
        except Exception as e:
            logger.error(f"Comment handler error: {e}")
            await context.chat_service.send_message(context.channel, f"Error saving comment: {e}")
