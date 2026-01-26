"""Debug why baneling bust patterns aren't matching"""
import json
import sys
import os
sys.path.insert(0, '.')

# Load comments
d = json.load(open('data/comments.json', encoding='utf-8'))

# Find the ГОСТ game (current game)
gost_game = None
for c in d['comments']:
    if c.get('game_data', {}).get('opponent_name') == 'ГОСТ':
        gost_game = c
        break

if not gost_game:
    print("ERROR: ГОСТ game not found")
    exit(1)

gost_build = gost_game['game_data']['build_order']
print(f"ГОСТ build has {len(gost_build)} steps")

# Find all baneling bust patterns
bane_patterns = [c for c in d['comments'] if 'bane' in c['comment'].lower() and c != gost_game]

print(f"\nFound {len(bane_patterns)} other baneling-related patterns")
print("\nComparing strategic items...")

# Extract strategic items for Zerg
def extract_strategic_items(build_order):
    """Extract strategic items like the ML analyzer does"""
    non_strategic = {'drone', 'overlord', 'zergling', 'queen'}
    strategic = {
        'spawningpool', 'hatchery', 'lair', 'hive', 'roachwarren', 'banelingnest', 
        'spire', 'hydraliskden', 'infestationpit', 'ultraliskcavern', 'lurkerden',
        'evolutionchamber', 'spinecrawler', 'sporecrawler',
        'roach', 'ravager', 'baneling', 'mutalisk', 'corruptor', 'lurker', 
        'hydralisk', 'broodlord', 'infestor', 'ultralisk', 'overseer',
        'metabolic boost', 'adrenal glands'
    }
    
    items = {}
    for i, step in enumerate(build_order[:120]):
        name = step.get('name', '').lower()
        if name not in non_strategic and name in strategic:
            if name not in items:
                items[name] = {'name': name, 'position': i}
    
    return items

gost_items = extract_strategic_items(gost_build)
print(f"\nГОСТ strategic items ({len(gost_items)}): {list(gost_items.keys())}")

# Count expansions in first 120 steps
def count_expansions(build_order):
    count = 0
    for step in build_order[:120]:
        if step.get('name', '').lower() == 'hatchery':
            count += 1
    return count

gost_expansions = count_expansions(gost_build)
print(f"ГОСТ expansions (first 120 steps): {gost_expansions}")

print("\n" + "="*60)
print("Checking each baneling pattern:")
print("="*60)

for pattern in bane_patterns[:15]:  # Check first 15
    comment = pattern['comment']
    gd = pattern.get('game_data', {})
    bo = gd.get('build_order', [])
    
    if not bo:
        print(f"\n'{comment}' - NO BUILD ORDER")
        continue
    
    pattern_items = extract_strategic_items(bo)
    pattern_expansions = count_expansions(bo)
    
    # Compare items
    gost_set = set(gost_items.keys())
    pattern_set = set(pattern_items.keys())
    
    matching = gost_set & pattern_set
    only_in_gost = gost_set - pattern_set
    only_in_pattern = pattern_set - gost_set
    
    print(f"\n'{comment}'")
    print(f"  Steps: {len(bo)}, Expansions: {pattern_expansions} (ГОСТ has {gost_expansions})")
    print(f"  Strategic items: {list(pattern_items.keys())}")
    print(f"  Matching: {list(matching)}")
    print(f"  Only in ГОСТ: {list(only_in_gost)}")
    print(f"  Only in pattern: {list(only_in_pattern)}")
    
    # Check for critical differences
    critical_diff = only_in_gost | only_in_pattern
    if critical_diff:
        print(f"  *** CRITICAL DIFFERENCES: {critical_diff}")

