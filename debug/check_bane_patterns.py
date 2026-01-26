"""Check baneling pattern build order lengths in comments.json - standalone"""
import json

with open('data/comments.json', encoding='utf-8') as f:
    d = json.load(f)

print("All baneling-related patterns and their build order sizes:")
print("="*70)

for c in d['comments']:
    comment = c.get('comment', '').lower()
    if 'bane' in comment:
        bo = c.get('game_data', {}).get('build_order', [])
        opponent = c.get('game_data', {}).get('opponent_name', 'Unknown')
        opp_race = c.get('game_data', {}).get('opponent_race', 'Unknown')
        print(f"{len(bo):4d} steps | {opp_race:7s} | {opponent:20s} | {c['comment'][:50]}")
