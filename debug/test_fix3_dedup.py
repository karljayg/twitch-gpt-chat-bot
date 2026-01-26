"""Test Fix 3: Deduplication - keep first occurrence only"""

# Simulate the extraction logic
strategic_items = {'hellion', 'factory', 'armory'}
non_strategic = {'scv', 'supplydepot'}

# Build with 18 Hellions (typical hellbat all-in)
hellbat_build = [
    {'supply': 12, 'name': 'SCV', 'time': 1},
    {'supply': 22, 'name': 'Factory', 'time': 108},
    {'supply': 26, 'name': 'Hellion', 'time': 190},
    {'supply': 28, 'name': 'Armory', 'time': 218},
    {'supply': 30, 'name': 'Hellion', 'time': 245},
    {'supply': 32, 'name': 'Hellion', 'time': 263},
    {'supply': 34, 'name': 'Hellion', 'time': 271},
    {'supply': 36, 'name': 'Hellion', 'time': 290},
    {'supply': 38, 'name': 'Hellion', 'time': 301},
    {'supply': 40, 'name': 'Hellion', 'time': 312},
    {'supply': 42, 'name': 'Hellion', 'time': 319},
    {'supply': 44, 'name': 'Hellion', 'time': 337},
]

# Extract WITH deduplication
seen_items = {}
for i, step in enumerate(hellbat_build):
    name = step.get('name', '').lower()
    timing = step.get('time', 0)
    
    if name in non_strategic:
        continue
    
    if name in strategic_items and name not in seen_items:
        seen_items[name] = {'name': name, 'timing': timing}

result = list(seen_items.values())

print("=== Fix 3 Test: Deduplication ===")
print(f"Build has {sum(1 for s in hellbat_build if s['name'].lower() == 'hellion')} Hellions")
print(f"Extracted items: {len(result)}")
for item in result:
    print(f"  {item['name']} @ {item['timing']}s")

if len(result) == 3:  # factory, hellion, armory (deduplicated)
    print("\n✓ PASS: Deduplication works! Only first occurrence kept.")
else:
    print(f"\n✗ FAIL: Expected 3 items, got {len(result)}")



