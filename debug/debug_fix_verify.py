"""Verify the fix - compare string time format vs int time format"""
import json
import sys
sys.path.insert(0, '.')

from settings import config

def get_strategic_item_names(race):
    strategic_items = set()
    if race in config.SC2_STRATEGIC_ITEMS:
        race_items = config.SC2_STRATEGIC_ITEMS[race]
        for category in ['buildings', 'units', 'upgrades']:
            if category in race_items:
                items = [item.strip().lower() for item in race_items[category].split(',')]
                strategic_items.update(items)
    return strategic_items

# FIXED version - handles both string and int time
def extract_strategic_items_from_build_FIXED(build_order, opponent_race):
    non_strategic = {
        'probe', 'scv', 'drone', 'mule',
        'pylon', 'supplydepot', 'overlord', 'overseer',
        'nexus', 'commandcenter', 'hatchery', 'lair', 'hive',
        'orbitalcommand', 'planetaryfortress'
    }
    
    strategic_items = get_strategic_item_names(opponent_race)
    
    seen_items = {}
    for i, step in enumerate(build_order):
        name = step.get('name', '').lower()
        raw_time = step.get('time', 0)
        
        # Normalize time to seconds
        if isinstance(raw_time, str) and ':' in raw_time:
            try:
                parts = raw_time.split(':')
                timing = int(parts[0]) * 60 + int(parts[1])
            except (ValueError, IndexError):
                timing = 0
        else:
            timing = raw_time if isinstance(raw_time, (int, float)) else 0
        
        if name in non_strategic:
            continue
        
        if name in strategic_items and name not in seen_items:
            seen_items[name] = {
                'name': name,
                'timing': timing,
                'position': i,
            }
    
    return list(seen_items.values())

# Simulate spawningtool output (string times like "1:37")
spawningtool_build = [
    {'supply': 12, 'name': 'SCV', 'time': '0:01'},
    {'supply': 13, 'name': 'SCV', 'time': '0:13'},
    {'supply': 14, 'name': 'SupplyDepot', 'time': '0:19'},
    {'supply': 19, 'name': 'Reaper', 'time': '1:37'},
    {'supply': 22, 'name': 'Factory', 'time': '1:48'},
    {'supply': 22, 'name': 'Bunker', 'time': '2:04'},
    {'supply': 26, 'name': 'Hellion', 'time': '3:10'},
    {'supply': 30, 'name': 'Armory', 'time': '3:38'},
]

# Simulate comments.json output (int times in seconds)
comments_build = [
    {'supply': 12, 'name': 'SCV', 'time': 1},
    {'supply': 13, 'name': 'SCV', 'time': 13},
    {'supply': 14, 'name': 'SupplyDepot', 'time': 19},
    {'supply': 19, 'name': 'Reaper', 'time': 97},
    {'supply': 22, 'name': 'Factory', 'time': 108},
    {'supply': 22, 'name': 'Bunker', 'time': 124},
    {'supply': 26, 'name': 'Hellion', 'time': 190},
    {'supply': 30, 'name': 'Armory', 'time': 218},
]

print("=== TESTING TIME NORMALIZATION ===")
print()

# Extract from spawningtool format (string times)
live_items = extract_strategic_items_from_build_FIXED(spawningtool_build, 'Terran')
print("From spawningtool (string times):")
for item in sorted(live_items, key=lambda x: x['timing']):
    print(f"  {item['name']} @ {item['timing']}s")

print()

# Extract from comments format (int times)
stored_items = extract_strategic_items_from_build_FIXED(comments_build, 'Terran')
print("From comments.json (int times):")
for item in sorted(stored_items, key=lambda x: x['timing']):
    print(f"  {item['name']} @ {item['timing']}s")

print()

# Check if they match
live_set = {(item['name'], item['timing']) for item in live_items}
stored_set = {(item['name'], item['timing']) for item in stored_items}

if live_set == stored_set:
    print("✓ MATCH! Both produce same strategic items with same timings.")
else:
    print("✗ MISMATCH!")
    print(f"  Live: {live_set}")
    print(f"  Stored: {stored_set}")



