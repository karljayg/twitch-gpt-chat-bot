"""Debug why no matches are found for a 688-step build"""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings.config as config

# What race was Flamer?
opponent_race = input("What race was Flamer? (Terran/Protoss/Zerg): ").strip()

# Check if race is in config
print(f"\nChecking SC2_STRATEGIC_ITEMS for {opponent_race}...")
if opponent_race in config.SC2_STRATEGIC_ITEMS:
    items = config.SC2_STRATEGIC_ITEMS[opponent_race]
    print(f"  Buildings: {items.get('buildings', '')[:50]}...")
    print(f"  Units: {items.get('units', '')[:50]}...")
else:
    print(f"  ERROR: {opponent_race} not in SC2_STRATEGIC_ITEMS!")
    print(f"  Available races: {list(config.SC2_STRATEGIC_ITEMS.keys())}")

# Check patterns for this race
with open('data/patterns.json', 'r', encoding='utf-8') as f:
    patterns = json.load(f)

race_patterns = [p for p in patterns.values() if p.get('race', '').lower() == opponent_race.lower()]
print(f"\nPatterns for {opponent_race}: {len(race_patterns)}")

if race_patterns:
    # Check first pattern's signature
    first = race_patterns[0]
    sig = first.get('signature', {})
    eg = sig.get('early_game', [])
    print(f"  First pattern: '{first.get('comment', '')[:40]}...'")
    print(f"  early_game items: {len(eg)}")
    if eg:
        print(f"  First 3 items: {[s.get('unit', '') for s in eg[:3]]}")

# Check comments for this race
with open('data/comments.json', 'r', encoding='utf-8') as f:
    comments_data = json.load(f)

race_comments = [c for c in comments_data.get('comments', []) 
                 if c.get('game_data', {}).get('opponent_race', '').lower() == opponent_race.lower()]
print(f"\nComments for {opponent_race}: {len(race_comments)}")

# Check if comments have build_order data
with_build = [c for c in race_comments if c.get('game_data', {}).get('build_order')]
print(f"  With build_order: {len(with_build)}")



