"""Test fair matching with scoped comparison"""
import json

with open('data/comments.json', encoding='utf-8') as f:
    d = json.load(f)

# Find ГОСТ game
gost_game = None
for c in d['comments']:
    if c.get('game_data', {}).get('opponent_name') == 'ГОСТ':
        gost_game = c
        break

gost_build = gost_game['game_data']['build_order']
print(f"ГОСТ build has {len(gost_build)} steps")

# Strategic items for Zerg
strategic = {
    'spawningpool', 'hatchery', 'lair', 'hive', 'roachwarren', 'banelingnest', 
    'spire', 'hydraliskden', 'infestationpit', 'ultraliskcavern', 'lurkerden',
    'evolutionchamber', 'spinecrawler', 'sporecrawler',
    'roach', 'ravager', 'baneling', 'mutalisk', 'corruptor', 'lurker', 
    'hydralisk', 'broodlord', 'infestor', 'ultralisk', 'overseer',
    'metabolic boost', 'adrenal glands'
}

def extract_items(build, limit):
    items = set()
    for step in build[:limit]:
        name = step.get('name', '').lower()
        if name in strategic:
            items.add(name)
    return items

# Compare ГОСТ items at 60 steps vs 120 steps
items_60 = extract_items(gost_build, 60)
items_120 = extract_items(gost_build, 120)

print(f"\nГОСТ items at 60 steps: {items_60}")
print(f"ГОСТ items at 120 steps: {items_120}")
print(f"\nMissing at 60 (but present at 120): {items_120 - items_60}")

# Check a 60-step pattern
for c in d['comments']:
    if 'ling bane' in c.get('comment', '').lower():
        bo = c.get('game_data', {}).get('build_order', [])
        if len(bo) == 60:
            pattern_items = extract_items(bo, 60)
            print(f"\nPattern '{c['comment']}' ({len(bo)} steps)")
            print(f"  Pattern items: {pattern_items}")
            print(f"  ГОСТ items (60 steps): {items_60}")
            print(f"  Matching: {pattern_items & items_60}")
            print(f"  Only in ГОСТ: {items_60 - pattern_items}")
            print(f"  Only in pattern: {pattern_items - items_60}")
            break

