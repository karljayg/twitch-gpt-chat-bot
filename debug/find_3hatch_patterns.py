"""Find all patterns that should match a 3 hatch ling build"""
import json

with open('data/patterns.json', 'r', encoding='utf-8') as f:
    patterns = json.load(f)

print("=== PATTERNS WITH '3 HATCH' OR 'LING' IN COMMENT ===\n")

three_hatch = []
ling_patterns = []
roach_patterns = []

for name, p in patterns.items():
    comment = p.get('comment', '').lower()
    race = p.get('race', '')
    
    if race.lower() != 'zerg':
        continue
    
    sig = p.get('signature', {})
    early_game = sig.get('early_game', [])
    
    # Count key buildings
    hatch_count = sum(1 for i in early_game if 'hatchery' in i.get('unit', '').lower())
    has_roach = any('roachwarren' in i.get('unit', '').lower() for i in early_game)
    has_bane = any('banelingnest' in i.get('unit', '').lower() for i in early_game)
    has_spire = any('spire' in i.get('unit', '').lower() for i in early_game)
    
    info = {
        'name': name,
        'comment': comment[:60],
        'hatch_count': hatch_count,
        'has_roach': has_roach,
        'has_bane': has_bane,
        'has_spire': has_spire
    }
    
    if '3 hatch' in comment or 'three hatch' in comment:
        three_hatch.append(info)
    elif 'ling' in comment and not has_roach:
        ling_patterns.append(info)
    elif 'roach' in comment:
        roach_patterns.append(info)

print("3 HATCH patterns:")
for p in three_hatch:
    print(f"  {p['comment']}")
    print(f"    Hatcheries: {p['hatch_count']}, Roach: {p['has_roach']}, Bane: {p['has_bane']}")

print(f"\n\nOTHER LING patterns (no roach, should match well with 3 hatch ling):")
for p in ling_patterns[:10]:
    print(f"  {p['comment']}")
    print(f"    Hatcheries: {p['hatch_count']}, Roach: {p['has_roach']}, Bane: {p['has_bane']}")

print(f"\n\nROACH patterns (should NOT match well with 3 hatch ling):")
for p in roach_patterns[:10]:
    print(f"  {p['comment']}")
    print(f"    Hatcheries: {p['hatch_count']}, Roach: {p['has_roach']}, Bane: {p['has_bane']}")



