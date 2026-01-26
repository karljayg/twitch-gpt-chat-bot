"""
Debug LIVE comparison - simulate exactly what happens during pattern matching
"""
import json
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("debug")

from api.ml_opponent_analyzer import MLOpponentAnalyzer

# Initialize analyzer
analyzer = MLOpponentAnalyzer()

# Load the pattern
with open('data/patterns.json', 'r', encoding='utf-8') as f:
    patterns = json.load(f)

# Find target pattern
target = None
for name, p in patterns.items():
    if '3 hatch ling all in' in p.get('comment', '').lower() and 'plus 1' in p.get('comment', '').lower():
        target = p
        target_name = name
        break

if not target:
    print("Pattern not found!")
    sys.exit(1)

print(f"Pattern: {target_name}")
print(f"Comment: {target.get('comment')}")

# Get the build order from comments.json
with open('data/comments.json', 'r', encoding='utf-8') as f:
    comments_data = json.load(f)

comment_id = target.get('comment_id', '')
target_comment = None
for c in comments_data.get('comments', []):
    if c.get('id') == comment_id:
        target_comment = c
        break

if not target_comment:
    print("Comment not found!")
    sys.exit(1)

build_order = target_comment.get('game_data', {}).get('build_order', [])
print(f"Build order: {len(build_order)} steps")

# Extract strategic items from build order (what happens for current game)
opponent_race = target_comment.get('game_data', {}).get('opponent_race', 'Zerg')
print(f"Opponent race: {opponent_race}")

new_build_items = analyzer._extract_strategic_items_from_build(build_order, opponent_race)
print(f"\nExtracted strategic items from build order ({len(new_build_items)}):")
for item in new_build_items:
    print(f"  {item['name']} @ {item['timing']}s")

# Extract strategic items from pattern signature
pattern_sig = target.get('signature', {})
pattern_items = analyzer._extract_strategic_items_from_signature(pattern_sig, opponent_race)
print(f"\nExtracted strategic items from pattern ({len(pattern_items)}):")
for item in pattern_items:
    print(f"  {item['name']} @ {item['timing']}s")

# Count expansions
expansion_names = {'hatchery', 'nexus', 'commandcenter'}
new_expansions = sum(1 for step in build_order if step.get('name', '').lower() in expansion_names)
pattern_early_game = pattern_sig.get('early_game', [])
pattern_expansions = sum(1 for step in pattern_early_game if step.get('unit', '').lower() in expansion_names)

print(f"\nExpansion counts: build={new_expansions}, pattern={pattern_expansions}")

# Now compare (with debug logging)
print("\n" + "=" * 60)
print("RUNNING COMPARISON")
print("=" * 60)

similarity = analyzer._compare_build_signatures(
    new_build_items, 
    pattern_items, 
    opponent_race, 
    logger,
    new_expansions=new_expansions,
    pattern_expansions=pattern_expansions
)

print(f"\n=== FINAL SIMILARITY: {similarity:.2%} ===")



