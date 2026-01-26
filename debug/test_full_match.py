"""Run full pattern matching using the correct method"""
import sys
sys.path.insert(0, '.')
import json
import logging

logging.basicConfig(level=logging.WARNING)

from api.ml_opponent_analyzer import get_ml_analyzer

# Load ГОСТ game
with open('data/comments.json', encoding='utf-8') as f:
    d = json.load(f)

gost_game = None
for c in d['comments']:
    if c.get('game_data', {}).get('opponent_name') == 'ГОСТ':
        gost_game = c
        break

build_order = gost_game['game_data']['build_order']
opponent_race = 'Zerg'

print(f"Build order has {len(build_order)} steps")

# Run pattern matching using the correct method
analyzer = get_ml_analyzer()
matches = analyzer.match_build_against_all_patterns(build_order, opponent_race, None)

print(f"Total matches: {len(matches)}")
print("\nAll baneling-related matches:")
print("="*60)

bane_matches = [m for m in matches if 'bane' in m.get('comment', '').lower()]
for i, m in enumerate(bane_matches):
    print(f"{i+1}. {m['similarity']*100:.0f}% - {m['comment']}")

print(f"\nTotal baneling matches: {len(bane_matches)}")
print("\n\nTop 10 overall matches:")
print("="*60)
for i, m in enumerate(matches[:10]):
    print(f"{i+1}. {m['similarity']*100:.0f}% - {m['comment']}")
