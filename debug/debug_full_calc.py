"""Full debug of similarity calculation for specific pattern"""
import sys
sys.path.insert(0, '.')
import json
import logging

logging.basicConfig(level=logging.DEBUG, format='%(message)s')
logger = logging.getLogger('debug')

from api.ml_opponent_analyzer import get_ml_analyzer

# Load ГОСТ game
with open('data/comments.json', encoding='utf-8') as f:
    d = json.load(f)

gost_bo = None
for c in d['comments']:
    if c.get('game_data', {}).get('opponent_name') == 'ГОСТ':
        gost_bo = c['game_data']['build_order']
        break

# Find "pool first ling bane all in" pattern
pool_pattern = None
for c in d['comments']:
    if c.get('comment', '') == 'pool first ling bane all in':
        pool_pattern = c
        break

print(f"ГОСТ build: {len(gost_bo)} steps")
print(f"Pattern: '{pool_pattern['comment']}' with {len(pool_pattern['game_data']['build_order'])} steps")

# Run full matching with debug logging
analyzer = get_ml_analyzer()
matches = analyzer.match_build_against_all_patterns(gost_bo, 'Zerg', logger)

# Find specific pattern result
for m in matches:
    if m['comment'] == 'pool first ling bane all in':
        print(f"\nResult: {m['similarity']*100:.1f}%")
        break

