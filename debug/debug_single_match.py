"""Debug why specific baneling patterns score low"""
import json

with open('data/comments.json', encoding='utf-8') as f:
    d = json.load(f)

# Find ГОСТ game
gost_bo = None
for c in d['comments']:
    if c.get('game_data', {}).get('opponent_name') == 'ГОСТ':
        gost_bo = c['game_data']['build_order']
        break

# Find specific patterns
patterns_to_check = [
    "pool first ling bane all in",
    "Baneling bust off two bases with speedlings",
    "13 pool ling bane all in"
]

expansion_names = {'hatchery'}

for target in patterns_to_check:
    for c in d['comments']:
        if c.get('comment', '').lower() == target.lower():
            bo = c['game_data'].get('build_order', [])
            pattern_len = len(bo)
            
            # Count expansions in pattern
            pattern_exp = sum(1 for step in bo if step.get('name', '').lower() in expansion_names)
            
            # Count expansions in ГОСТ at pattern's length (fair comparison)
            gost_exp_at_len = sum(1 for step in gost_bo[:pattern_len] if step.get('name', '').lower() in expansion_names)
            gost_exp_full = sum(1 for step in gost_bo[:120] if step.get('name', '').lower() in expansion_names)
            
            print(f"\n'{target}'")
            print(f"  Pattern length: {pattern_len} steps")
            print(f"  Pattern expansions: {pattern_exp}")
            print(f"  ГОСТ expansions at {pattern_len} steps: {gost_exp_at_len}")
            print(f"  ГОСТ expansions at 120 steps: {gost_exp_full}")
            print(f"  Expansion diff (at pattern len): {abs(gost_exp_at_len - pattern_exp)}")
            break

