import json
p=json.load(open('data/patterns.json'))

three_hatch = []
for name, pat in p.items():
    comment = pat.get('comment','').lower()
    if ('3 hatch' in comment or '3-hatch' in comment or 'three hatch' in comment) and pat.get('race','').lower() == 'zerg':
        sig = pat.get('signature',{})
        eg = sig.get('early_game',[])
        has_roach = any('roachwarren' in s.get('unit','').lower() for s in eg)
        has_bane = any('banelingnest' in s.get('unit','').lower() for s in eg)
        three_hatch.append((name, comment[:50], has_roach, has_bane))

print('3-HATCH PATTERNS (should match each other well):')
print()
# Group by tech
no_tech = [x for x in three_hatch if not x[2] and not x[3]]
bane_only = [x for x in three_hatch if x[3] and not x[2]]
roach_only = [x for x in three_hatch if x[2] and not x[3]]
both = [x for x in three_hatch if x[2] and x[3]]

print(f"NO TECH (pure ling - {len(no_tech)} patterns):")
for name, comment, _, _ in no_tech:
    print(f"  {comment}")

print(f"\nBANE ONLY ({len(bane_only)} patterns):")
for name, comment, _, _ in bane_only:
    print(f"  {comment}")

print(f"\nROACH (with or without bane - {len(roach_only) + len(both)} patterns):")
for name, comment, _, _ in roach_only + both:
    print(f"  {comment}")



