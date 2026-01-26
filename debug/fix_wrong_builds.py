"""Find and delete patterns where the build order doesn't match the comment description"""
import json

with open('data/patterns.json', 'r', encoding='utf-8') as f:
    patterns = json.load(f)

print("=" * 70)
print("FINDING PATTERNS WITH MISMATCHED BUILD DATA")
print("=" * 70)

to_delete = []

for name, p in patterns.items():
    comment = p.get('comment', '').lower()
    race = p.get('race', '').lower()
    sig = p.get('signature', {})
    eg = sig.get('early_game', [])
    
    if race != 'zerg':
        continue
    
    # Get key timings
    pool_time = next((s.get('time', 999) for s in eg if 'spawningpool' in s.get('unit', '').lower()), 999)
    first_hatch = next((s.get('time', 0) for s in eg if 'hatchery' in s.get('unit', '').lower()), 0)
    has_roach = any('roachwarren' in s.get('unit', '').lower() for s in eg)
    has_spire = any('spire' in s.get('unit', '').lower() for s in eg)
    
    issues = []
    
    # Check 1: "14 pool" or "12 pool" should have pool BEFORE first expansion
    if ('14 pool' in comment or '12 pool' in comment or '13 pool' in comment) and not 'hatch' in comment:
        if pool_time > first_hatch + 10:  # Pool should be before or within 10s of hatch for pool-first
            issues.append(f"Pool-first build but pool@{pool_time}s is AFTER hatch@{first_hatch}s")
    
    # Check 2: "roach" builds should have RoachWarren
    if 'roach' in comment and 'no roach' not in comment and not has_roach:
        # Check if it's a short game where roach might come later
        if len(eg) > 30:  # If we have 30+ steps, roach should appear
            issues.append("Comment mentions 'roach' but no RoachWarren in build")
    
    # Check 3: "muta" or "spire" builds should have Spire
    if ('muta' in comment or 'mutalisk' in comment) and 'to muta' not in comment and not has_spire:
        if len(eg) > 50:  # Spire comes later
            issues.append("Comment mentions 'muta' but no Spire in build")
    
    if issues:
        to_delete.append((name, p.get('comment', '')[:50], issues))

print(f"\nFound {len(to_delete)} patterns with mismatched build data:\n")
for name, comment, issues in to_delete:
    print(f"  {name}: '{comment}...'")
    for issue in issues:
        print(f"    - {issue}")
    print()

if to_delete:
    response = input("Delete these patterns? (y/N): ").strip().lower()
    if response == 'y':
        for name, _, _ in to_delete:
            del patterns[name]
        
        with open('data/patterns.json', 'w', encoding='utf-8') as f:
            json.dump(patterns, f, indent=2)
        print(f"\nDeleted {len(to_delete)} patterns. {len(patterns)} remaining.")
    else:
        print("Cancelled.")
else:
    print("No mismatched patterns found!")



