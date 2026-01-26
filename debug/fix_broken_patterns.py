"""
Find and fix patterns with broken build order data.
Zerg patterns should have Hatchery/SpawningPool - if they don't, the data is wrong.
"""
import json

with open('data/patterns.json', 'r', encoding='utf-8') as f:
    patterns = json.load(f)

print("=" * 70)
print("SCANNING FOR BROKEN ZERG PATTERNS")
print("(Zerg patterns without Hatchery or SpawningPool)")
print("=" * 70)

broken_patterns = []
good_patterns = []

for name, pat in patterns.items():
    race = pat.get('race', '').lower()
    if race != 'zerg':
        continue
    
    sig = pat.get('signature', {})
    eg = sig.get('early_game', [])
    
    # Check for expected Zerg buildings
    has_hatchery = any('hatchery' in s.get('unit', '').lower() for s in eg)
    has_pool = any('spawningpool' in s.get('unit', '').lower() for s in eg)
    has_drone = any('drone' in s.get('unit', '').lower() for s in eg)
    
    total_items = len(eg)
    comment = pat.get('comment', '')[:50]
    
    # If Zerg but no Hatchery/Pool/Drone - definitely wrong data
    if total_items > 10 and not has_hatchery and not has_pool:
        # Check what units ARE in there
        units = set(s.get('unit', '') for s in eg[:10])
        broken_patterns.append({
            'name': name,
            'comment': comment,
            'items': total_items,
            'sample_units': list(units)[:5]
        })
    elif has_hatchery or has_pool:
        good_patterns.append(name)

print(f"\nFound {len(broken_patterns)} broken Zerg patterns:")
print()

for bp in broken_patterns:
    print(f"  {bp['name']}: {bp['comment']}...")
    print(f"    Items: {bp['items']}, Sample units: {bp['sample_units']}")
    print()

print(f"Good Zerg patterns: {len(good_patterns)}")

# Offer to delete
if broken_patterns:
    print("\n" + "=" * 70)
    print("DELETING BROKEN PATTERNS")
    print("=" * 70)
    
    for bp in broken_patterns:
        del patterns[bp['name']]
        print(f"  Deleted: {bp['name']}")
    
    # Save
    with open('data/patterns.json', 'w', encoding='utf-8') as f:
        json.dump(patterns, f, indent=2)
    
    print(f"\nSaved patterns.json ({len(patterns)} patterns remaining)")



