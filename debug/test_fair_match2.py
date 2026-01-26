"""Test fair matching - find patterns with banelingnest"""
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

# Strategic items for Zerg
strategic = {
    'spawningpool', 'hatchery', 'lair', 'hive', 'roachwarren', 'banelingnest', 
    'spire', 'hydraliskden', 'spinecrawler', 'sporecrawler',
    'roach', 'baneling', 'mutalisk', 'hydralisk', 'metabolic boost'
}

def extract_items(build, limit):
    items = set()
    for step in build[:limit]:
        name = step.get('name', '').lower()
        if name in strategic:
            items.add(name)
    return items

gost_items_60 = extract_items(gost_build, 60)
print(f"ГОСТ items at 60 steps: {gost_items_60}\n")

# Find patterns that actually have banelingnest
print("Patterns with banelingnest in their build order:")
print("="*70)

for c in d['comments']:
    if 'bane' in c.get('comment', '').lower() and c != gost_game:
        bo = c.get('game_data', {}).get('build_order', [])
        if not bo:
            continue
        pattern_items = extract_items(bo, len(bo))
        if 'banelingnest' in pattern_items:
            overlap = gost_items_60 & pattern_items
            similarity = len(overlap) / max(len(gost_items_60), len(pattern_items))
            print(f"{len(bo):3d} steps | {c['comment'][:40]:<40} | items: {len(pattern_items)} | overlap: {len(overlap)}/{len(gost_items_60)} = {similarity:.0%}")

