"""Debug what strategic items are extracted and compared"""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import settings.config as config

def get_strategic_items_set(race):
    """Get all strategic items for a race as a set of lowercase names"""
    race_items = config.SC2_STRATEGIC_ITEMS.get(race, {})
    all_items = set()
    for category in ['buildings', 'units', 'upgrades']:
        items_str = race_items.get(category, '')
        for item in items_str.split(','):
            item = item.strip().lower()
            if item:
                all_items.add(item)
    return all_items

# Load the pattern
with open('data/patterns.json', 'r', encoding='utf-8') as f:
    patterns = json.load(f)

# Find the 3 hatch ling pattern
target_pattern = None
for name, p in patterns.items():
    if '3 hatch ling all in' in p.get('comment', '').lower():
        target_pattern = p
        print(f"Found pattern: {name}")
        print(f"Comment: {p.get('comment')}")
        break

if not target_pattern:
    print("Pattern not found!")
    sys.exit(1)

# Get Zerg strategic items
zerg_items = get_strategic_items_set('Zerg')
print(f"\nZerg strategic items ({len(zerg_items)} total):")
print(zerg_items)

# Check what's in the pattern signature
sig = target_pattern.get('signature', {})
early_game = sig.get('early_game', [])

print(f"\nPattern early_game has {len(early_game)} items")
print("\nStrategic items in pattern:")
strategic_in_pattern = []
non_strategic = []

for item in early_game:
    unit_name = item.get('unit', item.get('name', ''))
    if unit_name.lower() in zerg_items:
        strategic_in_pattern.append(f"{unit_name} @ {item.get('time', 0)}s")
    else:
        non_strategic.append(unit_name)

print(f"  Strategic ({len(strategic_in_pattern)}):")
for s in strategic_in_pattern[:20]:
    print(f"    {s}")
if len(strategic_in_pattern) > 20:
    print(f"    ... and {len(strategic_in_pattern) - 20} more")

print(f"\n  Non-strategic ({len(set(non_strategic))}):")
for s in sorted(set(non_strategic)):
    print(f"    {s}")

# Count key strategic buildings
hatch_count = sum(1 for i in early_game if 'hatchery' in i.get('unit', '').lower())
pool_time = next((i.get('time', 0) for i in early_game if 'spawningpool' in i.get('unit', '').lower()), 'N/A')
ling_count = sum(1 for i in early_game if 'zergling' in i.get('unit', '').lower())

print(f"\n=== KEY STRATEGY INDICATORS ===")
print(f"Hatchery count: {hatch_count}")
print(f"SpawningPool timing: {pool_time}s")
print(f"Zergling entries: {ling_count}")
