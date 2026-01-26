"""Check the stored data for the target comment"""
import json

with open('data/comments.json', 'r') as f:
    d = json.load(f)

for c in d['comments']:
    if '1 base reaper bunker' in c.get('comment', '').lower():
        print("=== STORED COMMENT DATA ===")
        print(f"Comment: {c.get('comment')}")
        print(f"Replay ID: {c.get('replay_id')}")
        print()
        
        game_data = c.get('game_data', {})
        print("Game Data keys:", list(game_data.keys()))
        print(f"Opponent: {game_data.get('opponent_name')}")
        print(f"Race: {game_data.get('opponent_race')}")
        print(f"Map: {game_data.get('map')}")
        print()
        
        bo = game_data.get('build_order', [])
        print(f"Build order: {len(bo)} steps")
        
        # Show all strategic items with their times
        strategic = ['reaper', 'factory', 'bunker', 'hellion', 'armory', 'starport', 'marine', 'marauder', 'tank']
        print("\nStrategic items in stored build:")
        for step in bo:
            name = step.get('name', '').lower()
            if name in strategic:
                time_val = step.get('time')
                print(f"  {step.get('name')} @ time={time_val} (type={type(time_val).__name__})")
        
        break



