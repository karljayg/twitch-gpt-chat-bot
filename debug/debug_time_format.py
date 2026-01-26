"""Check time format in comments.json"""
import json

with open('data/comments.json', 'r') as f:
    d = json.load(f)

for c in d['comments']:
    if '1 base reaper bunker' in c.get('comment', '').lower():
        bo = c['game_data']['build_order']
        print("First 10 steps from comments.json:")
        for step in bo[:10]:
            time_val = step.get('time')
            print(f"  supply={step.get('supply')}, name={step.get('name')}, time={time_val} (type={type(time_val).__name__})")
        break



