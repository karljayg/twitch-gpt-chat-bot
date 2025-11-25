from collections import defaultdict
from settings import config
import re

class GameSummarizer:
    @staticmethod
    def generate_summary(replay_data, winning_players, losing_players):
        replay_summary = ""
        
        # Players and Map
        players_list = []
        if isinstance(replay_data.get('players'), dict):
            for p_data in replay_data['players'].values():
                players_list.append(f"{p_data['name']}: {p_data['race']}")
        
        players_str = ', '.join(players_list)
        
        replay_summary += f"Players: {players_str}\n"
        replay_summary += f"Map: {replay_data.get('map', 'Unknown')}\n"
        replay_summary += f"Region: {replay_data.get('region', 'Unknown')}\n"
        replay_summary += f"Game Type: {replay_data.get('game_type', 'Unknown')}\n"
        replay_summary += f"Timestamp: {replay_data.get('unix_timestamp', 0)}\n"
        replay_summary += f"Winners: {winning_players}\n"
        replay_summary += f"Losers: {losing_players}\n"
        
        # Duration
        duration_info = GameSummarizer.calculate_duration(replay_data)
        total_seconds = duration_info['totalSeconds']
        replay_summary += f"Game Duration: {duration_info['gameDuration']}\n\n"
        
        # Units Lost
        if 'players' in replay_data:
            units_lost_summary = {pk: pd.get('unitsLost', []) for pk, pd in replay_data['players'].items()}
            for pk, units_lost in units_lost_summary.items():
                player_name = replay_data['players'][pk]['name']
                replay_summary += f"Units Lost by {player_name}\n"
                
                units_lost_aggregate = defaultdict(int)
                if units_lost:
                    for unit in units_lost:
                        name = unit.get('name', "N/A")
                        units_lost_aggregate[name] += 1
                    for name, count in units_lost_aggregate.items():
                        replay_summary += f"{name}: {count}\n"
                else:
                    replay_summary += "None \n"
                replay_summary += '\n'

        # Build Orders
        if total_seconds < 600:
            base_build_count = 60
        else:
            base_build_count = 90
            
        total_players = len(replay_data.get('players', {}))
        if total_players > 2:
            build_order_count = base_build_count / 2
        else:
            build_order_count = base_build_count
            
        if 'players' in replay_data:
            build_orders = {pk: pd.get('buildOrder', []) for pk, pd in replay_data['players'].items()}
            
            # Sort players (Opponent first, Streamer last)
            # STRICTLY identify the streamer
            player_order = []
            player_accounts_lower = [name.lower() for name in config.SC2_PLAYER_ACCOUNTS]
            
            streamer_pk = None
            opponent_pk = None
            
            for pk, pd in replay_data['players'].items():
                if pd['name'].lower() in player_accounts_lower:
                    streamer_pk = pk
                else:
                    opponent_pk = pk # In 1v1, this is unique. In team games, list logic handles it.
            
            # Reconstruct order: Opponents first, then Streamer
            # This ensures "Opponent Build" comes first in text, if iterating
            player_keys = list(replay_data['players'].keys())
            sorted_keys = sorted(player_keys, key=lambda k: 1 if k == streamer_pk else 0)
            
            for pk in sorted_keys:
                if pk not in build_orders: continue
                
                build_order = build_orders[pk]
                player_name = replay_data['players'][pk]['name']
                
                # Explicitly label build orders based on identity
                is_streamer = (pk == streamer_pk)
                
                header_name = config.STREAMER_NICKNAME if is_streamer else player_name
                replay_summary += f"{header_name}'s Build Order (first set of steps):\n"
                
                for order in build_order[:int(build_order_count)]:
                    order_time = order.get('time', '')
                    name = order.get('name', '')
                    supply = order.get('supply', '')
                    replay_summary += f"Time: {order_time}, Name: {name}, Supply: {supply}\n"
                replay_summary += '\n'
                
        # Anonymize Streamer Name in the rest of the text (already handled in headers above, but good for other sections)
        for player_name in config.SC2_PLAYER_ACCOUNTS:
            pattern = re.compile(re.escape(player_name), re.IGNORECASE)
            replay_summary = pattern.sub(config.STREAMER_NICKNAME, replay_summary)
            
        return replay_summary

    @staticmethod
    def calculate_duration(replay_data):
        res = {}
        frames = replay_data.get('frames', 0)
        fps = replay_data.get('frames_per_second', 16)
        if fps == 0: fps = 16
            
        total_seconds = frames / fps
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        
        res["totalSeconds"] = total_seconds
        res["gameDuration"] = f"{minutes}m {seconds}s"
        return res

