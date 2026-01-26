import json

with open('data/comments.json', 'r') as f:
    d = json.load(f)

for c in d['comments']:
    if '1 base reaper bunker' in c.get('comment', ''):
        bo = c['game_data'].get('build_order', [])
        print(f"Comment: {c['comment']}")
        print(f"Build order steps in comments.json: {len(bo)}")
        if bo:
            print(f"First 5: {[s['name'] for s in bo[:5]]}")
            print(f"Last 5: {[s['name'] for s in bo[-5:]]}")
        break



