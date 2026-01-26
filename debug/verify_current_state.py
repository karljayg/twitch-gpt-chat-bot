"""
Verify current state of pattern matching - NO CHANGES, just testing
"""
import sys
sys.path.insert(0, '.')

from api.ml_opponent_analyzer import MLOpponentAnalyzer
from unittest.mock import MagicMock

print("=" * 60)
print("VERIFICATION TEST - Current Main Branch State")
print("=" * 60)

analyzer = MLOpponentAnalyzer()
logger = MagicMock()

# Test 1: Check if race filtering works
print("\n[TEST 1] Race Filtering")
print("-" * 40)

# Simulate Zerg build
zerg_build = [
    {'supply': 13, 'name': 'SpawningPool', 'time': 88},
    {'supply': 14, 'name': 'Zergling', 'time': 100},
]

zerg_items = analyzer._extract_strategic_items_from_build(zerg_build, 'Zerg')
print(f"Zerg build extracts: {[i['name'] for i in zerg_items]}")

# Test 2: Check expansion counting
print("\n[TEST 2] Expansion Detection")
print("-" * 40)

# Build with 2 hatcheries
two_hatch_build = [
    {'supply': 13, 'name': 'Hatchery', 'time': 50},
    {'supply': 17, 'name': 'SpawningPool', 'time': 88},
    {'supply': 20, 'name': 'Hatchery', 'time': 150},
]

items = analyzer._extract_strategic_items_from_build(two_hatch_build, 'Zerg')
hatch_count = sum(1 for i in items if i['name'] == 'hatchery')
print(f"2-hatch build - Hatcheries in strategic items: {hatch_count}")
print(f"All strategic items: {[i['name'] for i in items]}")

if hatch_count == 0:
    print("⚠️  WARNING: Hatcheries NOT in strategic items - expansion penalty won't work!")
else:
    print("✓ Hatcheries detected")

# Test 3: Check time format handling
print("\n[TEST 3] Time Format Handling")
print("-" * 40)

# Build with string time (spawningtool format)
string_time_build = [
    {'supply': 13, 'name': 'RoachWarren', 'time': '2:00'},  # String format
]

try:
    items = analyzer._extract_strategic_items_from_build(string_time_build, 'Zerg')
    if items:
        timing = items[0].get('timing')
        print(f"String time '2:00' extracted as: {timing} (type: {type(timing).__name__})")
        if timing == 120:
            print("✓ Time correctly converted to seconds")
        elif timing == '2:00':
            print("⚠️  WARNING: Time NOT converted - still string!")
        else:
            print(f"⚠️  Unexpected value: {timing}")
    else:
        print("⚠️  No items extracted")
except Exception as e:
    print(f"✗ ERROR: {e}")

# Test 4: Check patterns.json race labels
print("\n[TEST 4] Patterns.json Race Labels")
print("-" * 40)

import json
with open('data/patterns.json', 'r') as f:
    patterns = json.load(f)

protoss_keywords = ['adept', 'stalker', 'zealot', 'carrier', 'void ray', 'oracle', 'gateway']
wrong_labels = 0

for key in patterns.keys():
    if key.startswith('pattern_'):
        p = patterns[key]
        comment = p.get('comment', '').lower()
        race = p.get('race', 'unknown')
        
        if any(kw in comment for kw in protoss_keywords) and race != 'protoss':
            wrong_labels += 1

print(f"Protoss patterns with wrong race labels: {wrong_labels}")
if wrong_labels == 0:
    print("✓ Race labels correct")
else:
    print(f"⚠️  WARNING: {wrong_labels} patterns have wrong race!")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)



