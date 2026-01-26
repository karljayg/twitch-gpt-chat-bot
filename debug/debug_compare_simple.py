"""
Simple debug comparison - standalone without heavy imports
"""
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

def extract_from_build(build_order, strategic_items):
    """Extract and deduplicate strategic items from build order"""
    seen = {}
    for step in build_order:
        name = step.get('name', '').lower()
        timing = step.get('time', 0)
        if isinstance(timing, str) and ':' in timing:
            parts = timing.split(':')
            timing = int(parts[0]) * 60 + int(parts[1])
        if name in strategic_items and name not in seen:
            seen[name] = {'name': name, 'timing': timing}
    return list(seen.values())

def extract_from_signature(signature, strategic_items):
    """Extract and deduplicate strategic items from pattern signature"""
    seen = {}
    for step in signature.get('early_game', []):
        name = step.get('unit', '').lower()
        timing = step.get('time', 0)
        if isinstance(timing, str) and ':' in timing:
            parts = timing.split(':')
            timing = int(parts[0]) * 60 + int(parts[1])
        if name in strategic_items and name not in seen:
            seen[name] = {'name': name, 'timing': timing}
    return list(seen.values())

# Load data
with open('data/patterns.json', 'r', encoding='utf-8') as f:
    patterns = json.load(f)
with open('data/comments.json', 'r', encoding='utf-8') as f:
    comments_data = json.load(f)

# Find target
target = None
for name, p in patterns.items():
    if '3 hatch ling all in' in p.get('comment', '').lower() and 'plus 1' in p.get('comment', '').lower():
        target = p
        target_name = name
        break

print(f"Pattern: {target_name}")
print(f"Comment: {target.get('comment')}")

# Get corresponding comment by matching comment text
target_comment_text = target.get('comment', '')
target_comment = None
for c in comments_data.get('comments', []):
    if c.get('comment', '') == target_comment_text or c.get('raw_comment', '') == target_comment_text:
        target_comment = c
        break

if not target_comment:
    print(f"Comment not found! Looking for: {target_comment_text[:50]}...")
    # Try partial match
    for c in comments_data.get('comments', []):
        if target_comment_text[:30].lower() in c.get('comment', '').lower():
            target_comment = c
            print(f"Found partial match: {c.get('comment', '')[:50]}...")
            break

if not target_comment:
    print("Still not found, using pattern's game_data directly")
    target_comment = {'game_data': target.get('game_data', {})}

# Get strategic items
zerg_items = get_strategic_items_set('Zerg')

# Extract from build order (simulating current game)
build_order = target_comment.get('game_data', {}).get('build_order', [])
build_items = extract_from_build(build_order, zerg_items)

# Extract from pattern signature
pattern_sig = target.get('signature', {})
pattern_items = extract_from_signature(pattern_sig, zerg_items)

print(f"\n=== FROM BUILD ORDER ({len(build_items)} items) ===")
for item in sorted(build_items, key=lambda x: x['timing']):
    print(f"  {item['name']} @ {item['timing']}s")

print(f"\n=== FROM PATTERN SIGNATURE ({len(pattern_items)} items) ===")
for item in sorted(pattern_items, key=lambda x: x['timing']):
    print(f"  {item['name']} @ {item['timing']}s")

# Compare
print("\n=== COMPARISON ===")
build_dict = {i['name']: i['timing'] for i in build_items}
pattern_dict = {i['name']: i['timing'] for i in pattern_items}

all_items = set(build_dict.keys()) | set(pattern_dict.keys())
matching = set(build_dict.keys()) & set(pattern_dict.keys())

print(f"Items in build: {set(build_dict.keys())}")
print(f"Items in pattern: {set(pattern_dict.keys())}")
print(f"Matching: {matching}")
print(f"Only in build: {set(build_dict.keys()) - set(pattern_dict.keys())}")
print(f"Only in pattern: {set(pattern_dict.keys()) - set(build_dict.keys())}")

print("\n=== TIMING COMPARISON ===")
for item in matching:
    build_t = build_dict[item]
    pattern_t = pattern_dict[item]
    diff = abs(build_t - pattern_t)
    status = "✓ identical" if diff == 0 else f"⚠️ diff={diff}s"
    print(f"  {item}: build={build_t}s, pattern={pattern_t}s {status}")

# Expansion count
expansion_names = {'hatchery', 'nexus', 'commandcenter'}
build_exp = sum(1 for step in build_order if step.get('name', '').lower() in expansion_names)
pattern_exp = sum(1 for step in pattern_sig.get('early_game', []) if step.get('unit', '').lower() in expansion_names)
print(f"\n=== EXPANSION COUNT ===")
print(f"Build: {build_exp}, Pattern: {pattern_exp}")
if build_exp != pattern_exp:
    print(f"❌ MISMATCH - this causes penalty!")

