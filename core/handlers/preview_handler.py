"""Handler for 'please preview' command - runs pre-game analysis using last replay data."""

import json
import logging
import os
import re
import spawningtool.parser
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
            args = (args or "").strip()
            opponent_name = None
            opponent_race = None
            streamer_race = "Unknown"
            current_map = "Unknown"
            replay_target_label = "latest replay"
            use_pattern_validation_preview = False
            versus_name = ""
            replay_summary = ""
            replay_date = "Unknown"
            replay_result = "Observed"
            replay_duration = "Unknown"

            if args:
                try:
                    replay_id = int(args)
                except ValueError:
                    await context.chat_service.send_message(
                        context.channel,
                        "Usage: please preview [ReplayID] (or please review [ReplayID])",
                    )
                    return

                if replay_id < 0:
                    n_back = abs(replay_id)
                    replay_data = await self._load_replay_data_n_games_ago(n_back)
                    if not replay_data:
                        await context.chat_service.send_message(
                            context.channel,
                            f"Preview failed - could not find replay from {n_back} game(s) ago.",
                        )
                        return

                    opponent_info = self._extract_opponent_info(replay_data)
                    if not opponent_info:
                        await context.chat_service.send_message(
                            context.channel,
                            "Preview failed - couldn't identify opponent from replay data.",
                        )
                        return

                    opponent_name = opponent_info['name']
                    opponent_race = opponent_info['race']
                    streamer_race = opponent_info['streamer_race']
                    current_map = replay_data.get('map', 'Unknown')
                    replay_target_label = f"{n_back} game(s) ago"
                elif replay_id == 0:
                    await context.chat_service.send_message(
                        context.channel,
                        "Preview supports ReplayID (>0) or negative offset (<0). Example: please preview 25593 or please preview -3",
                    )
                    return
                else:
                    db = getattr(self.twitch_bot, "db", None)
                    if db is None or not hasattr(db, "get_replay_by_id"):
                        await context.chat_service.send_message(
                            context.channel,
                            "Preview failed - database replay lookup is not available.",
                        )
                        return

                    replay_info = db.get_replay_by_id(replay_id)
                    if not replay_info:
                        await context.chat_service.send_message(
                            context.channel,
                            f"Preview failed - Replay ID {replay_id} not found.",
                        )
                        return

                    opponent_name, opponent_race, streamer_race, versus_name = self._resolve_players_for_preview(replay_info)
                    current_map = replay_info.get("map", "Unknown")
                    replay_target_label = f"ReplayID {replay_id}"
                    replay_summary = str(replay_info.get("replay_summary", "") or "")
                    replay_date = replay_info.get("date", "Unknown")
                    replay_result = replay_info.get("result", "Observed")
                    replay_duration = replay_info.get("duration", "Unknown")
                    use_pattern_validation_preview = True
            else:
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
                f"Previewing opponent analysis for {opponent_name} ({opponent_race}) from {replay_target_label}..."
            )
            
            success = False
            if use_pattern_validation_preview and hasattr(self.twitch_bot, "_display_pattern_validation"):
                build_order = self._parse_build_order_from_summary(replay_summary, opponent_name)
                if build_order:
                    game_data = {
                        "replay_id": replay_id,
                        "opponent_name": opponent_name,
                        "opponent_race": opponent_race,
                        "versus_name": versus_name,
                        "map": current_map,
                        "date": replay_date,
                        "result": replay_result,
                        "duration": replay_duration,
                        "build_order": build_order,
                        "existing_comment": replay_info.get("existing_comment"),
                        "suppress_followup_prompt": True,
                    }
                    self.twitch_bot._display_pattern_validation(game_data, logger)
                    success = True

            if not success:
                # Run the analysis (no context history for preview - don't pollute live context)
                import asyncio
                loop = asyncio.get_running_loop()

                # Run in executor since it's synchronous
                # Preview/review: bundle expert notes + pattern + build + last-meeting in ONE GenAI user message.
                # Saved line must be copied verbatim (see pregame_intel); live game start still uses inline=False.
                success = await loop.run_in_executor(
                    None,
                    lambda: self.opponent_analysis_service.analyze_opponent(
                        opponent_name,
                        opponent_race,
                        streamer_race,
                        current_map,
                        [],
                        inline_saved_notes_in_last_meeting=True,
                    ),
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

    def _resolve_players_for_preview(self, replay_info: dict):
        """Pick names from replay_summary players/build owner when available."""
        replay_summary = str(replay_info.get("replay_summary", "") or "")
        players = []
        race_by_name = {}

        players_line_match = re.search(r"^Players:\s*(.+)$", replay_summary, re.IGNORECASE | re.MULTILINE)
        if players_line_match:
            for part in players_line_match.group(1).split(","):
                part = part.strip()
                if ":" not in part:
                    continue
                name, race = part.split(":", 1)
                name = name.strip()
                race = race.strip()
                if name:
                    players.append(name)
                    race_by_name[name.lower()] = race

        build_owner = None
        owner_match = re.search(r"^(.+?)'s Build Order", replay_summary, re.IGNORECASE | re.MULTILINE)
        if owner_match:
            build_owner = owner_match.group(1).strip()

        opponent_name = str(replay_info.get("opponent", "Unknown") or "Unknown")
        opponent_race = str(replay_info.get("opponent_race", "Unknown") or "Unknown")

        if build_owner and (not players or any(p.lower() == build_owner.lower() for p in players)):
            opponent_name = build_owner
            opponent_race = race_by_name.get(build_owner.lower(), opponent_race)
        elif players:
            opponent_name = players[0]
            opponent_race = race_by_name.get(opponent_name.lower(), opponent_race)

        streamer_race = str(replay_info.get("streamer_race", "Unknown") or "Unknown")
        if players:
            for p in players:
                if p.lower() != opponent_name.lower():
                    streamer_race = race_by_name.get(p.lower(), streamer_race)
                    break

        versus_name = ""
        if players:
            for p in players:
                if p.lower() != opponent_name.lower():
                    versus_name = p
                    break

        return opponent_name, opponent_race, streamer_race, versus_name

    def _parse_build_order_from_summary(self, summary_text: str, player_name: str) -> list:
        """Parse player's build order from Replay_Summary text."""
        build_order = []
        if not summary_text or not player_name:
            return build_order

        pattern = rf"{re.escape(player_name)}'s Build Order.*?:\n(.*?)(?:\n\n[A-Z]|\n\n|\Z)"
        match = re.search(pattern, summary_text, re.DOTALL | re.IGNORECASE)
        if not match:
            return build_order

        build_section = match.group(1)
        for line in build_section.strip().split('\n'):
            line = line.strip()
            if not line.startswith('Time:'):
                continue
            time_match = re.search(r'Time:\s*(\d+:\d+)', line)
            name_match = re.search(r'Name:\s*(\w+)', line)
            supply_match = re.search(r'Supply:\s*(\d+)', line)
            if not (time_match and name_match):
                continue
            mins, secs = time_match.group(1).split(':')
            build_order.append({
                'time': int(mins) * 60 + int(secs),
                'name': name_match.group(1),
                'supply': int(supply_match.group(1)) if supply_match else 0,
            })
        return build_order

    async def _load_replay_data_n_games_ago(self, n_back: int) -> dict:
        """Load replay_data for N games ago by replay-file recency."""
        import asyncio
        loop = asyncio.get_running_loop()
        replay_path = await loop.run_in_executor(None, self._find_nth_latest_replay_file, n_back)
        if not replay_path:
            return None
        replay_data = await loop.run_in_executor(None, self._parse_replay_file, replay_path)
        return replay_data if isinstance(replay_data, dict) else None

    def _find_nth_latest_replay_file(self, n_back: int):
        """Find nth latest replay file by modified time. n_back=0 latest."""
        try:
            if not os.path.isdir(config.REPLAYS_FOLDER):
                return None
            ext = config.REPLAYS_FILE_EXTENSION
            if not ext.startswith("."):
                ext = "." + ext

            candidates = []
            for root, _dirs, files in os.walk(config.REPLAYS_FOLDER):
                for filename in files:
                    if filename.endswith(ext):
                        path = os.path.join(root, filename)
                        try:
                            candidates.append((os.path.getmtime(path), path))
                        except OSError:
                            continue

            if not candidates:
                return None
            candidates.sort(key=lambda x: x[0], reverse=True)
            idx = max(0, int(n_back))
            if idx >= len(candidates):
                return None
            return candidates[idx][1]
        except Exception as e:
            logger.error(f"Preview - error finding nth latest replay file: {e}")
            return None

    def _parse_replay_file(self, replay_path: str):
        """Parse replay file to replay_data dict."""
        try:
            if not os.path.exists(replay_path):
                return None
            return spawningtool.parser.parse_replay(replay_path)
        except Exception as e:
            logger.error(f"Preview - error parsing replay file {replay_path}: {e}")
            return None
    
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

