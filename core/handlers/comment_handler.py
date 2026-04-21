import logging
import asyncio
import json
import os
from core.command_service import ICommandHandler, CommandContext
from core.interfaces import IReplayRepository
from settings import config
from utils.player_comment_args import split_replay_ref_prefix

logger = logging.getLogger(__name__)

class CommentHandler(ICommandHandler):
    """Handler for 'player comment' commands"""
    def __init__(self, replay_repo: IReplayRepository, pattern_learner):
        self.replay_repo = replay_repo
        self.pattern_learner = pattern_learner
        
    async def handle(self, context: CommandContext, args: str):
        # Check for Y/N response to overwrite confirmation FIRST (before processing as new comment)
        twitch_bot = None
        if hasattr(context.chat_service, 'twitch_bot'):
            twitch_bot = context.chat_service.twitch_bot

        target_replay_id = None
        if twitch_bot and hasattr(twitch_bot, 'pattern_learning_context') and twitch_bot.pattern_learning_context:
            target_replay_id = (
                (twitch_bot.pattern_learning_context.get('game_data') or {}).get('replay_id')
            )
        
        if twitch_bot and hasattr(twitch_bot, 'pending_player_comment') and twitch_bot.pending_player_comment:
            msg_lower = args.strip().lower()
            if msg_lower in ['y', 'yes']:
                logger.info("User confirmed overwrite of existing comment")
                try:
                    pending = twitch_bot.pending_player_comment
                    comment_text = pending['comment']
                    replay_info = pending['replay']
                    
                    # Overwrite the comment
                    success = await self._save_comment(comment_text, replay_info.get('replay_id'))
                    
                    if success and self.pattern_learner:
                        loop = asyncio.get_running_loop()
                        game_data = {
                            'replay_id': replay_info.get('replay_id'),
                            'opponent_name': replay_info['opponent'],
                            'map': replay_info['map'],
                            'date': replay_info['date'],
                            'result': replay_info['result'],
                            'duration': replay_info['duration']
                        }
                        
                        # Get build_order from last replay JSON
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
                        
                        response = f"Overwritten comment for game vs {replay_info['opponent']} on {replay_info['map']} ({replay_info['date']}): '{comment_text}'"
                        await context.chat_service.send_message(context.channel, response)
                    else:
                        await context.chat_service.send_message(context.channel, "Failed to save comment")
                        
                except Exception as e:
                    logger.error(f"Error overwriting comment: {e}")
                    await context.chat_service.send_message(context.channel, f"Error saving comment: {str(e)}")
                finally:
                    twitch_bot.pending_player_comment = None
                return
                
            elif msg_lower in ['n', 'no']:
                logger.info("User declined overwrite, checking for newer replay")
                try:
                    pending = twitch_bot.pending_player_comment
                    original_timestamp = pending['timestamp']
                    comment_text = pending['comment']
                    
                    # Get latest replay again to see if new game happened
                    latest_replay = await self.replay_repo.get_latest_replay()
                    
                    if not latest_replay:
                        await context.chat_service.send_message(context.channel, "No replays found")
                    elif latest_replay.get('timestamp', 0) > original_timestamp:
                        # New game exists!
                        if latest_replay.get('existing_comment'):
                            await context.chat_service.send_message(
                                context.channel, 
                                f"Newer replay vs {latest_replay['opponent']} also has a comment - cannot save"
                            )
                        else:
                            # Save to new replay
                            success = await self._save_comment(comment_text, latest_replay.get('replay_id'))
                            if success and self.pattern_learner:
                                loop = asyncio.get_running_loop()
                                game_data = {
                                    'opponent_name': latest_replay['opponent'],
                                    'map': latest_replay['map'],
                                    'date': latest_replay['date'],
                                    'result': latest_replay['result'],
                                    'duration': latest_replay['duration']
                                }
                                
                                # Get build_order
                                try:
                                    replay_json_path = config.LAST_REPLAY_JSON_FILE
                                    if os.path.exists(replay_json_path):
                                        with open(replay_json_path, 'r') as f:
                                            replay_data = json.load(f)
                                        player_accounts_lower = [name.lower() for name in config.SC2_PLAYER_ACCOUNTS]
                                        for p_key, p_data in replay_data.get('players', {}).items():
                                            if p_data.get('name', '').lower() not in player_accounts_lower:
                                                game_data['build_order'] = p_data.get('buildOrder', [])
                                                game_data['opponent_race'] = p_data.get('race', 'Unknown')
                                                break
                                except Exception as e:
                                    logger.warning(f"Could not load build order: {e}")
                                
                                await loop.run_in_executor(
                                    None,
                                    self.pattern_learner._process_new_comment,
                                    game_data,
                                    comment_text
                                )
                                await loop.run_in_executor(None, self.pattern_learner.save_patterns_to_file)
                                
                                response = f"Saved comment to newer replay vs {latest_replay['opponent']} on {latest_replay['map']}: '{comment_text}'"
                                await context.chat_service.send_message(context.channel, response)
                            else:
                                await context.chat_service.send_message(context.channel, "Failed to save comment")
                    else:
                        await context.chat_service.send_message(context.channel, "User declined to overwrite existing comment")
                except Exception as e:
                    logger.error(f"Error handling declined overwrite: {e}")
                finally:
                    twitch_bot.pending_player_comment = None
                return
        
        # Strip "player comment" or "player comments" prefix if present (command_service passes full message)
        comment_text = args.strip()
        comment_lower = comment_text.lower()
        if comment_lower.startswith('player comments '):
            comment_text = comment_text[16:].strip()  # "player comments " = 16 chars
        elif comment_lower.startswith('player comment '):
            comment_text = comment_text[15:].strip()  # "player comment " = 15 chars

        explicit_ref, comment_text = split_replay_ref_prefix(comment_text)
        if explicit_ref is not None and not (comment_text or '').strip():
            await context.chat_service.send_message(
                context.channel,
                "Usage: player comment <ReplayID|-N> <your comment>. Examples: "
                "'player comment 25456 ling bane' or 'player comment -1 one-liner'",
            )
            return
        
        if not comment_text:
            await context.chat_service.send_message(context.channel, "Please provide comment text after 'player comment'")
            return
        
        # Check if there's an active pattern learning context from the legacy system
        # If so, we need to process this as a natural language response to the suggestions
        
        if (
            explicit_ref is None
            and twitch_bot
            and hasattr(twitch_bot, 'pattern_learning_context')
            and twitch_bot.pattern_learning_context
        ):
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
                        
                        # NLP chooses pattern/AI/skip; custom saves use the typed line verbatim.
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
                        elif action == 'custom':
                            # Expert text must be saved verbatim; NLP may only choose the action, not rewrite the line.
                            logger.info("NLP action=custom — keeping typed comment_text unchanged for DB save")
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
            
        try:
            latest_replay = None
            db = getattr(self.replay_repo, 'db', None)
            loop = asyncio.get_running_loop()

            if explicit_ref is not None:
                if not db:
                    await context.chat_service.send_message(
                        context.channel,
                        "Replay-specific player comments require database access on this bot instance.",
                    )
                    return
                if explicit_ref > 0:
                    if not hasattr(db, 'get_replay_by_id'):
                        await context.chat_service.send_message(
                            context.channel,
                            "Database client does not support replay-by-id lookup.",
                        )
                        return
                    latest_replay = await loop.run_in_executor(None, db.get_replay_by_id, int(explicit_ref))
                    if not latest_replay:
                        await context.chat_service.send_message(
                            context.channel,
                            f"Replay ID {explicit_ref} not found.",
                        )
                        return
                    if latest_replay.get('replay_id') is None:
                        latest_replay['replay_id'] = int(explicit_ref)
                else:
                    n_back = abs(int(explicit_ref))
                    if not hasattr(db, 'get_replay_by_recency_offset'):
                        await context.chat_service.send_message(
                            context.channel,
                            "Database client does not support -N (games ago) replay lookup.",
                        )
                        return
                    latest_replay = await loop.run_in_executor(None, db.get_replay_by_recency_offset, n_back)
                    if not latest_replay:
                        await context.chat_service.send_message(
                            context.channel,
                            f"Could not find replay from {n_back} game(s) ago.",
                        )
                        return
            elif target_replay_id and db and hasattr(db, 'get_replay_by_id'):
                latest_replay = await loop.run_in_executor(None, db.get_replay_by_id, int(target_replay_id))
                if latest_replay and latest_replay.get('replay_id') is None:
                    latest_replay['replay_id'] = int(target_replay_id)
            if not latest_replay:
                # Fallback to latest replay behavior
                latest_replay = await self.replay_repo.get_latest_replay()
            
            if not latest_replay:
                await context.chat_service.send_message(context.channel, "No replays found in database - please play a game first")
                return
                
            opponent = latest_replay.get('opponent', 'Unknown')
            map_name = latest_replay.get('map', 'Unknown')
            game_date = latest_replay.get('date', 'Unknown')
            existing_comment = latest_replay.get('existing_comment')
            
            # Log for debugging
            logger.info(f"Checking for existing comment: existing_comment={existing_comment!r} (type={type(existing_comment).__name__}, truthy={bool(existing_comment)})")
            
            # Check if comment already exists - ask for confirmation before overwriting
            # existing_comment can be None, empty string, or actual text
            # Use explicit check: not None and not empty after stripping whitespace
            has_existing_comment = existing_comment is not None and str(existing_comment).strip() != ''
            
            logger.info(f"Has existing comment check result: {has_existing_comment}")
            
            if has_existing_comment:
                # Store pending state for Y/N confirmation in legacy bot
                if twitch_bot:
                    twitch_bot.pending_player_comment = {
                        'comment': comment_text,
                        'replay': latest_replay,
                        'timestamp': latest_replay.get('timestamp', 0),
                        'replay_id': latest_replay.get('replay_id'),
                    }
                
                rid = latest_replay.get('replay_id')
                scope = f"replay {rid}" if rid else f"last game vs {opponent}"
                response = (
                    f"There is already a comment for {scope} on {map_name} ({game_date}). "
                    f"Overwrite? Y/N"
                )
                await context.chat_service.send_message(context.channel, response)
                logger.info(f"Existing comment found, asking for overwrite confirmation")
                return
            
            # No existing comment - save directly
            # Update DB
            success = await self._save_comment(comment_text, latest_replay.get('replay_id'))
            
            if success:
                # Update Pattern Learner (Legacy component, likely sync)
                # We still need to run this in executor if it does file I/O
                if self.pattern_learner:
                    loop = asyncio.get_running_loop()
                    game_data = {
                        'replay_id': latest_replay.get('replay_id'),
                        'opponent_name': opponent,
                        'map': map_name,
                        'date': game_date,
                        'result': latest_replay.get('result', 'Unknown'),
                        'duration': latest_replay.get('duration', 'Unknown')
                    }
                    
                    # Get build_order from last replay JSON (saved after each game)
                    # IMPORTANT: Verify both opponent name AND game date match to avoid stale data
                    try:
                        replay_json_path = config.LAST_REPLAY_JSON_FILE
                        if os.path.exists(replay_json_path):
                            with open(replay_json_path, 'r') as f:
                                replay_data = json.load(f)
                            
                            # Verify game timestamp matches (within 5 minutes tolerance)
                            json_timestamp = replay_data.get('unix_timestamp', 0)
                            from datetime import datetime
                            try:
                                db_date = datetime.strptime(game_date, '%Y-%m-%d %H:%M:%S')
                                json_date = datetime.fromtimestamp(json_timestamp)
                                time_diff = abs((db_date - json_date).total_seconds())
                                if time_diff > 300:  # More than 5 minutes difference
                                    logger.warning(f"Game date mismatch: DB={game_date}, JSON={json_date} (diff={time_diff}s) - JSON may be from a different game")
                                    # Don't use stale JSON data
                                    raise ValueError("Stale JSON data")
                            except (ValueError, TypeError) as e:
                                if "Stale" not in str(e):
                                    logger.warning(f"Could not compare timestamps: {e}")
                                raise
                            
                            # Find opponent's build order - MATCH BY NAME to avoid wrong game's data
                            opponent_lower = opponent.lower()
                            found_opponent = False
                            for p_key, p_data in replay_data.get('players', {}).items():
                                if p_data.get('name', '').lower() == opponent_lower:
                                    game_data['build_order'] = p_data.get('buildOrder', [])
                                    game_data['opponent_race'] = p_data.get('race', 'Unknown')
                                    logger.info(f"Loaded {len(game_data['build_order'])} build order steps for {opponent} from last replay (timestamp verified)")
                                    found_opponent = True
                                    break
                            
                            if not found_opponent:
                                logger.warning(f"Opponent '{opponent}' not found in last_replay_data.json - replay may be from a different game")
                    except Exception as e:
                        logger.warning(f"Could not load build order from replay JSON: {e} - comment will be saved without build order")
                    
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

    async def _save_comment(self, comment_text: str, replay_id=None) -> bool:
        """Save comment to specific replay when replay_id is known, otherwise latest replay."""
        try:
            loop = asyncio.get_running_loop()
            db = getattr(self.replay_repo, 'db', None)
            if replay_id and db and hasattr(db, 'update_player_comments_by_replay_id'):
                return await loop.run_in_executor(
                    None,
                    db.update_player_comments_by_replay_id,
                    int(replay_id),
                    comment_text,
                )
            return await self.replay_repo.update_comment(comment_text)
        except Exception as e:
            logger.error(f"Error saving comment (replay_id={replay_id}): {e}")
            return False
