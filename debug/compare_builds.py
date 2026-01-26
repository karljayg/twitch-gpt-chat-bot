"""Compare the strategic items in 3 hatch vs 14 pool vs roach builds"""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings.config as config

def get_strategic_set(race):
    items = config.SC2_STRATEGIC_ITEMS.get(race, {})
    all_items = set()
    for cat in ['buildings', 'units', 'upgrades']:
        for item in items.get(cat, '').split(','):
            item = item.strip().lower()
            if item:
                all_items.add(item)
    return all_items

with open('data/patterns.json', 'r', encoding='utf-8') as f:
    patterns = json.load(f)

zerg_strategic = get_strategic_set('Zerg')

# Find specific patterns
targets = [
    "player comments 3 hatch ling all in with plus 1 upgrade",
    "14 pool lings, then muta",
    "roach ling all in counter"
]

for target in targets:
    print(f"\n{'='*60}")
    for name, p in patterns.items():
        if target.lower() in p.get('comment', '').lower():
            print(f"Pattern: {p.get('comment', '')[:60]}")
            sig = p.get('signature', {})
            eg = sig.get('early_game', [])
            
            # Count key items
            hatch_count = sum(1 for s in eg if 'hatchery' in s.get('unit', '').lower())
            pool_timing = next((s.get('time', 'N/A') for s in eg if 'spawningpool' in s.get('unit', '').lower()), 'N/A')
            has_roach = any('roachwarren' in s.get('unit', '').lower() for s in eg)
            has_bane = any('banelingnest' in s.get('unit', '').lower() for s in eg)
            speed_timing = next((s.get('time', 'N/A') for s in eg if 'metabolic' in s.get('unit', '').lower()), 'N/A')
            
            print(f"  Hatcheries: {hatch_count}")
            print(f"  SpawningPool timing: {pool_timing}s")
            print(f"  Metabolic Boost timing: {speed_timing}s")
            print(f"  RoachWarren: {'YES' if has_roach else 'NO'}")
            print(f"  BanelingNest: {'YES' if has_bane else 'NO'}")
            
            # List strategic items
            strategic = []
            for s in eg:
                unit = s.get('unit', '').lower()
                if unit in zerg_strategic:
                    strategic.append(f"{unit}@{s.get('time', 0)}s")
            print(f"  Strategic items: {strategic[:10]}")
            break



