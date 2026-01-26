"""Check if the stored comment game matches current game being processed"""
import json

with open('data/comments.json', 'r') as f:
    d = json.load(f)

for c in d['comments']:
    if '1 base reaper bunker' in c.get('comment', '').lower():
        game_data = c.get('game_data', {})
        print("=== STORED COMMENT ===")
        print(f"Comment: {c.get('comment')}")
        print(f"Opponent: {game_data.get('opponent_name')}")
        print(f"Map: {game_data.get('map')}")
        print(f"Date: {game_data.get('date')}")
        print(f"Replay ID: {c.get('replay_id')}")
        print(f"Build order steps: {len(game_data.get('build_order', []))}")
        
        bo = game_data.get('build_order', [])
        if bo:
            # Show first 10 and strategic items
            print("\nFirst 10 steps:")
            for step in bo[:10]:
                print(f"  {step['supply']}: {step['name']} @ {step['time']}s")
        break



