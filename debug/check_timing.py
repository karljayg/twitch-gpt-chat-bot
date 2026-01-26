"""Check when strategic items appear in ГОСТ game"""
import json

with open('data/comments.json', encoding='utf-8') as f:
    d = json.load(f)

for c in d['comments']:
    if c.get('game_data', {}).get('opponent_name') == 'ГОСТ':
        bo = c['game_data']['build_order']
        print(f"ГОСТ build has {len(bo)} steps")
        print("\nStrategic items with step position:")
        strategic = {'spawningpool', 'hatchery', 'lair', 'hive', 'banelingnest', 
                    'baneling', 'spinecrawler', 'sporecrawler', 'metabolic boost'}
        for i, step in enumerate(bo[:150]):  # Check first 150
            name = step.get('name', '').lower()
            if name in strategic:
                time_str = step.get('time', '?')
                print(f"  Step {i:3d} @ {time_str}: {name}")
        break

