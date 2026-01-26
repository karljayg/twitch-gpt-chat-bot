"""Debug why exact same game doesn't match at 100%"""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import settings.config as config

def get_strategic_items_set(race):
    race_items = config.SC2_STRATEGIC_ITEMS.get(race, {})
    all_items = set()
    for category in ['buildings', 'units', 'upgrades']:
        items_str = race_items.get(category, '')
        for item in items_str.split(','):
            item = item.strip().lower()
            if item:
                all_items.add(item)
    return all_items

# Load pattern
with open('data/patterns.json', 'r', encoding='utf-8') as f:
    patterns = json.load(f)

# Load comments (has full build order)
with open('data/comments.json', 'r', encoding='utf-8') as f:
    comments_data = json.load(f)

# Find the 3 hatch ling pattern
target = None
target_comment = None
for name, p in patterns.items():
    if '3 hatch ling all in' in p.get('comment', '').lower() and 'plus 1' in p.get('comment', '').lower():
        target = p
        target_name = name
        # Find corresponding comment
        comment_id = p.get('comment_id', '')
        for c in comments_data.get('comments', []):
            if c.get('id') == comment_id:
                target_comment = c
                break
        break

if not target:
    print("Pattern not found!")
    sys.exit(1)

print(f"Pattern: {target_name}")
print(f"Comment: {target.get('comment')}")

# Get strategic items
zerg_items = get_strategic_items_set('Zerg')

# Analyze pattern signature
sig = target.get('signature', {})
early_game = sig.get('early_game', [])

print("\n=== PATTERN SIGNATURE (what's stored) ===")
pattern_strategic = []
for item in early_game:
    unit = item.get('unit', '').lower()
    if unit in zerg_items:
        pattern_strategic.append({
            'name': unit,
            'timing': item.get('time', 0),
            'supply': item.get('supply', 0)
        })
        print(f"  {unit} @ {item.get('time', 0)}s (supply {item.get('supply', 0)})")

# Count expansions in pattern
expansion_names = {'hatchery', 'nexus', 'commandcenter'}
pattern_expansions = sum(1 for step in early_game if step.get('unit', '').lower() in expansion_names)
print(f"\nPattern expansion count: {pattern_expansions}")

# Check the game_data build order (what would be extracted from replay)
if target_comment:
    build_order = target_comment.get('game_data', {}).get('build_order', [])
    print(f"\n=== COMMENT BUILD ORDER (full: {len(build_order)} steps) ===")
    
    comment_strategic = []
    for step in build_order:
        name = step.get('name', '').lower()
        if name in zerg_items:
            if not any(s['name'] == name for s in comment_strategic):  # Dedupe
                comment_strategic.append({
                    'name': name,
                    'timing': step.get('time', 0),
                    'supply': step.get('supply', 0)
                })
                print(f"  {name} @ {step.get('time', 0)}s (supply {step.get('supply', 0)})")
    
    # Count expansions in build order
    comment_expansions = sum(1 for step in build_order if step.get('name', '').lower() in expansion_names)
    print(f"\nComment build order expansion count: {comment_expansions}")
    
    # Compare
    print("\n=== COMPARISON ===")
    if pattern_expansions != comment_expansions:
        print(f"❌ EXPANSION MISMATCH: pattern={pattern_expansions}, comment={comment_expansions}")
        diff = abs(pattern_expansions - comment_expansions)
        if diff == 1:
            print(f"   Penalty: 40% (multiplier 0.6)")
        elif diff == 2:
            print(f"   Penalty: 70% (multiplier 0.3)")
    else:
        print(f"✓ Expansion count matches: {pattern_expansions}")
    
    # Compare strategic items
    pattern_items = {s['name'] for s in pattern_strategic}
    comment_items = {s['name'] for s in comment_strategic}
    
    print(f"\nStrategic items in pattern: {pattern_items}")
    print(f"Strategic items in comment: {comment_items}")
    
    missing_in_comment = pattern_items - comment_items
    missing_in_pattern = comment_items - pattern_items
    
    if missing_in_comment:
        print(f"❌ In pattern but not comment: {missing_in_comment}")
    if missing_in_pattern:
        print(f"❌ In comment but not pattern: {missing_in_pattern}")
    if not missing_in_comment and not missing_in_pattern:
        print("✓ Strategic items match perfectly")
    
    # Compare timings
    print("\n=== TIMING COMPARISON ===")
    for ps in pattern_strategic:
        for cs in comment_strategic:
            if ps['name'] == cs['name']:
                diff = abs(ps['timing'] - cs['timing'])
                status = "✓" if diff < 30 else "⚠️"
                print(f"  {ps['name']}: pattern={ps['timing']}s, comment={cs['timing']}s, diff={diff}s {status}")



