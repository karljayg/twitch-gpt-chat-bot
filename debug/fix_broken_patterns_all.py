"""
Find and fix patterns with broken build order data for ALL races.
"""
import json

with open('data/patterns.json', 'r', encoding='utf-8') as f:
    patterns = json.load(f)

print("=" * 70)
print("SCANNING FOR BROKEN PATTERNS (ALL RACES)")
print("=" * 70)

# Define expected buildings for each race
race_markers = {
    'zerg': ['hatchery', 'spawningpool', 'drone'],
    'terran': ['commandcenter', 'barracks', 'scv', 'supplydepot'],
    'protoss': ['nexus', 'gateway', 'probe', 'pylon']
}

broken_patterns = []

for name, pat in patterns.items():
    race = pat.get('race', '').lower()
    if race not in race_markers:
        continue
    
    sig = pat.get('signature', {})
    eg = sig.get('early_game', [])
    
    if len(eg) < 5:
        continue  # Skip sparse patterns
    
    # Get units in pattern
    units_lower = [s.get('unit', '').lower() for s in eg]
    
    # Check if ANY expected marker for this race exists
    expected = race_markers[race]
    has_race_marker = any(any(m in u for u in units_lower) for m in expected)
    
    if not has_race_marker:
        # Check what race it actually looks like
        actual_race = 'unknown'
        for check_race, markers in race_markers.items():
            if any(any(m in u for u in units_lower) for m in markers):
                actual_race = check_race
                break
        
        broken_patterns.append({
            'name': name,
            'comment': pat.get('comment', '')[:50],
            'tagged_race': race,
            'actual_race': actual_race,
            'items': len(eg)
        })

print(f"\nFound {len(broken_patterns)} patterns with wrong race data:")
print()

for bp in broken_patterns:
    print(f"  {bp['name']}: {bp['comment']}...")
    print(f"    Tagged: {bp['tagged_race']}, Actual: {bp['actual_race']}, Items: {bp['items']}")
    print()

if broken_patterns:
    print("\n" + "=" * 70)
    print("DELETING BROKEN PATTERNS")
    print("=" * 70)
    
    for bp in broken_patterns:
        del patterns[bp['name']]
        print(f"  Deleted: {bp['name']}")
    
    with open('data/patterns.json', 'w', encoding='utf-8') as f:
        json.dump(patterns, f, indent=2)
    
    print(f"\nSaved patterns.json ({len(patterns)} patterns remaining)")
else:
    print("No additional broken patterns found!")



