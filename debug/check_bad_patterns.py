"""Check the 2 patterns with wrong race labels"""
import json

with open('data/patterns.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for pattern_name in ['pattern_227', 'pattern_452']:
    p = data.get(pattern_name, {})
    if p:
        print(f"\n{pattern_name}:")
        print(f"  comment: {p.get('comment', '')[:70]}...")
        print(f"  race (tagged): {p.get('race')}")
        gd = p.get('game_data', {})
        print(f"  game_data.opponent_race: {gd.get('opponent_race', 'MISSING')}")
        print(f"  game_data.opponent_name: {gd.get('opponent_name', 'MISSING')}")
    else:
        print(f"\n{pattern_name}: NOT FOUND")



