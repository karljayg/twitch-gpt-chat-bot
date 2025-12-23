"""Handler for 'please preview' command - runs pre-game analysis using last replay data."""

import json
import logging
import os
from core.command_service import ICommandHandler, CommandContext
import settings.config as config

logger = logging.getLogger(__name__)


class PreviewHandler(ICommandHandler):
    """Handler for 'please preview' command - previews opponent analysis from last replay."""
    
    def __init__(self, opponent_analysis_service, twitch_bot):
        self.opponent_analysis_service = opponent_analysis_service
        self.twitch_bot = twitch_bot
    
    async def handle(self, context: CommandContext, args: str):
        # Only allow broadcaster to preview
        if context.author.lower() != config.PAGE.lower():
            logger.info(f"Preview command rejected - not from broadcaster (from: {context.author})")
            return
        
        try:
            # Load last replay data
            replay_data = self._load_last_replay_data()
            
            if not replay_data:
                await context.chat_service.send_message(
                    context.channel,
                    "Preview failed - no recent replay data found. Play a game or run 'please retry' first."
                )
                return
            
            # Extract opponent info from replay data
            opponent_info = self._extract_opponent_info(replay_data)
            
            if not opponent_info:
                await context.chat_service.send_message(
                    context.channel,
                    "Preview failed - couldn't identify opponent from replay data."
                )
                return
            
            opponent_name = opponent_info['name']
            opponent_race = opponent_info['race']
            streamer_race = opponent_info['streamer_race']
            current_map = replay_data.get('map', 'Unknown')
            
            logger.info(f"Running preview for: {opponent_name} ({opponent_race}) vs {streamer_race} on {current_map}")
            
            await context.chat_service.send_message(
                context.channel,
                f"Previewing opponent analysis for {opponent_name} ({opponent_race})..."
            )
            
            # Run the analysis (no context history for preview - don't pollute live context)
            import asyncio
            loop = asyncio.get_running_loop()
            
            # Run in executor since it's synchronous
            success = await loop.run_in_executor(
                None,
                self.opponent_analysis_service.analyze_opponent,
                opponent_name,
                opponent_race,
                streamer_race,
                current_map,
                []  # Empty context history
            )
            
            if not success:
                await context.chat_service.send_message(
                    context.channel,
                    "Preview completed but no analysis was generated."
                )
                
        except Exception as e:
            logger.error(f"Error during preview: {e}", exc_info=True)
            await context.chat_service.send_message(
                context.channel,
                f"Preview failed: {e}"
            )
    
    def _load_last_replay_data(self) -> dict:
        """Load the last_replay_data.json file."""
        json_path = os.path.join('temp', 'last_replay_data.json')
        
        if not os.path.exists(json_path):
            logger.warning(f"No replay data file found at {json_path}")
            return None
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load replay data: {e}")
            return None
    
    def _extract_opponent_info(self, replay_data: dict) -> dict:
        """Extract opponent name, race, and streamer race from replay data."""
        players = replay_data.get('players', {})
        
        if not players:
            logger.warning("No players found in replay data")
            return None
        
        streamer_accounts_lower = [name.lower() for name in config.SC2_PLAYER_ACCOUNTS]
        
        opponent_name = None
        opponent_race = None
        streamer_race = None
        
        # Players dict uses "1", "2" as keys, actual name is in player_data['name']
        for player_id, player_data in players.items():
            player_name = player_data.get('name', '')
            
            if player_name.lower() in streamer_accounts_lower:
                # This is the streamer
                streamer_race = player_data.get('race', 'Unknown')
            else:
                # This is the opponent
                opponent_name = player_name
                opponent_race = player_data.get('race', 'Unknown')
        
        if not opponent_name:
            logger.warning("Could not identify opponent in replay data")
            return None
        
        if not streamer_race:
            # Fallback - assume first non-opponent is streamer
            streamer_race = "Unknown"
        
        return {
            'name': opponent_name,
            'race': opponent_race,
            'streamer_race': streamer_race
        }

