"""Debug strategic items for specific pattern"""
import json

with open('data/comments.json', encoding='utf-8') as f:
    d = json.load(f)

# Find games
gost_bo = None
pool_bo = None
for c in d['comments']:
    if c.get('game_data', {}).get('opponent_name') == 'ГОСТ':
        gost_bo = c['game_data']['build_order']
    if c.get('comment', '') == 'pool first ling bane all in':
        pool_bo = c['game_data']['build_order']

strategic = {
    'spawningpool', 'hatchery', 'lair', 'hive', 'roachwarren', 'banelingnest', 
    'spire', 'hydraliskden', 'spinecrawler', 'sporecrawler', 'evolutionchamber',
    'roach', 'baneling', 'mutalisk', 'hydralisk', 'lurker', 'metabolic boost'
}

def extract(bo, limit):
    items = {}
    for i, step in enumerate(bo[:limit]):
        name = step.get('name', step.get('unit', '')).lower()
        if name in strategic and name not in items:
            items[name] = {'pos': i, 'time': step.get('time', '?')}
    return items

# Compare at pattern length (120 steps)
limit = len(pool_bo)
print(f"Comparing at {limit} steps:")
print(f"\nГОСТ strategic items (first {limit}):")
gost_items = extract(gost_bo, limit)
for name, info in sorted(gost_items.items(), key=lambda x: x[1]['pos']):
    print(f"  {info['pos']:3d} @ {info['time']}: {name}")

print(f"\nPattern 'pool first ling bane all in' ({limit} steps):")
pool_items = extract(pool_bo, limit)
for name, info in sorted(pool_items.items(), key=lambda x: x[1]['pos']):
    print(f"  {info['pos']:3d} @ {info['time']}: {name}")

print(f"\nOverlap: {set(gost_items.keys()) & set(pool_items.keys())}")
print(f"Only in ГОСТ: {set(gost_items.keys()) - set(pool_items.keys())}")
print(f"Only in pattern: {set(pool_items.keys()) - set(gost_items.keys())}")

