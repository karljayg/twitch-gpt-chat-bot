"""Debug the EXACT flow of match_build_against_all_patterns"""
import json
import sys
sys.path.insert(0, '.')

from settings import config

# Load the stored comment
with open('data/comments.json', 'r') as f:
    d = json.load(f)

target_comment = None
for c in d['comments']:
    if '1 base reaper bunker' in c.get('comment', '').lower():
        target_comment = c
        break

game_data = target_comment.get('game_data', {})
build_data = game_data.get('build_order', [])
comment_race = game_data.get('opponent_race', 'unknown')

print("=== Step 1: Create pattern signature from stored comment ===")
print(f"Stored race: {comment_race}")
print(f"Pattern race (lowercased): {comment_race.lower()}")

# Lines 106-114 of ml_opponent_analyzer.py
early_game_signature = []
for i, step in enumerate(build_data):
    early_game_signature.append({
        'unit': step.get('name', ''),  # Convert 'name' to 'unit'
        'time': step.get('time', 0),
        'supply': step.get('supply', 0),
        'count': 1,
        'order': i + 1
    })

pattern_signature = {'early_game': early_game_signature}
print(f"Pattern signature has {len(early_game_signature)} steps")

print("\n=== Step 2: Simulate live build order from spawningtool ===")
# The live build would come from spawningtool with string times
# But for this test, assume the SAME data (since it's the same game)
live_build_order = build_data  # Same data

print(f"Live build has {len(live_build_order)} steps")

print("\n=== Step 3: Extract strategic items ===")

def get_strategic_item_names(race):
    strategic_items = set()
    if race in config.SC2_STRATEGIC_ITEMS:
        race_items = config.SC2_STRATEGIC_ITEMS[race]
        for category in ['buildings', 'units', 'upgrades']:
            if category in race_items:
                items = [item.strip().lower() for item in race_items[category].split(',')]
                strategic_items.update(items)
    return strategic_items

# From live build (uses opponent_race = "Terran" from live game)
opponent_race = "Terran"  # This is what the live game would have
print(f"Live opponent_race: '{opponent_race}'")
print(f"Config has key '{opponent_race}': {opponent_race in config.SC2_STRATEGIC_ITEMS}")

live_strategic = get_strategic_item_names(opponent_race)
print(f"Strategic items for {opponent_race}: {len(live_strategic)} items")

# Check both Terran and terran
print(f"Config has 'Terran': {'Terran' in config.SC2_STRATEGIC_ITEMS}")
print(f"Config has 'terran': {'terran' in config.SC2_STRATEGIC_ITEMS}")

# Now extract from live build
non_strategic = {
    'probe', 'scv', 'drone', 'mule',
    'pylon', 'supplydepot', 'overlord', 'overseer',
    'nexus', 'commandcenter', 'hatchery', 'lair', 'hive',
    'orbitalcommand', 'planetaryfortress'
}

seen_items = {}
for i, step in enumerate(live_build_order):
    name = step.get('name', '').lower()
    raw_time = step.get('time', 0)
    
    # Normalize time
    if isinstance(raw_time, str) and ':' in raw_time:
        parts = raw_time.split(':')
        timing = int(parts[0]) * 60 + int(parts[1])
    else:
        timing = raw_time if isinstance(raw_time, (int, float)) else 0
    
    if name in non_strategic:
        continue
    
    if name in live_strategic and name not in seen_items:
        seen_items[name] = {'name': name, 'timing': timing}

live_items = list(seen_items.values())
print(f"\nLive build strategic items ({len(live_items)}):")
for item in sorted(live_items, key=lambda x: x['timing']):
    print(f"  {item['name']} @ {item['timing']}s")

# Extract from pattern signature
seen_items_pat = {}
for i, step in enumerate(pattern_signature['early_game']):
    unit_name = step.get('unit', '').lower()
    raw_time = step.get('time', 0)
    
    # Normalize time
    if isinstance(raw_time, str) and ':' in raw_time:
        parts = raw_time.split(':')
        timing = int(parts[0]) * 60 + int(parts[1])
    else:
        timing = raw_time if isinstance(raw_time, (int, float)) else 0
    
    if unit_name in live_strategic and unit_name not in seen_items_pat:
        seen_items_pat[unit_name] = {'name': unit_name, 'timing': timing}

pattern_items = list(seen_items_pat.values())
print(f"\nPattern strategic items ({len(pattern_items)}):")
for item in sorted(pattern_items, key=lambda x: x['timing']):
    print(f"  {item['name']} @ {item['timing']}s")

# Compare
live_set = {(item['name'], item['timing']) for item in live_items}
pat_set = {(item['name'], item['timing']) for item in pattern_items}

print(f"\n=== Comparison ===")
if live_set == pat_set:
    print("IDENTICAL - should be 100%")
else:
    print("DIFFERENT!")
    print(f"  In live but not pattern: {live_set - pat_set}")
    print(f"  In pattern but not live: {pat_set - live_set}")



