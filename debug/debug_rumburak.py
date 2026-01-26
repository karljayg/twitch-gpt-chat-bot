import json

with open('data/comments.json', 'r') as f:
    d = json.load(f)

print("All comments with Rumburak opponent:")
for c in d['comments']:
    gd = c.get('game_data', {})
    if 'rumburak' in str(gd.get('opponent_name', '')).lower():
        print(f"  Comment: {c.get('comment')}")
        print(f"    Map: {gd.get('map')}")
        print(f"    Date: {gd.get('date')}")
        print(f"    Steps: {len(gd.get('build_order', []))}")
        print()



