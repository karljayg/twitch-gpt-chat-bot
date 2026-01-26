import json
p=json.load(open('data/patterns.json'))

print("PURE LING 3-HATCH PATTERNS - checking build order quality:")
print()

for name, pat in p.items():
    comment = pat.get('comment','').lower()
    if ('3 hatch' in comment or '3-hatch' in comment) and pat.get('race','').lower() == 'zerg':
        sig = pat.get('signature',{})
        eg = sig.get('early_game',[])
        has_roach = any('roachwarren' in s.get('unit','').lower() for s in eg)
        has_bane = any('banelingnest' in s.get('unit','').lower() for s in eg)
        
        # Only pure ling patterns
        if not has_roach and not has_bane:
            hatch_count = sum(1 for s in eg if 'hatchery' in s.get('unit','').lower())
            pool_time = next((s.get('time',0) for s in eg if 'spawningpool' in s.get('unit','').lower()), 'N/A')
            total_items = len(eg)
            
            print(f"{pat.get('comment','')[:55]}")
            print(f"  Total early_game items: {total_items}")
            print(f"  Hatcheries: {hatch_count}")
            print(f"  SpawningPool timing: {pool_time}")
            print()



