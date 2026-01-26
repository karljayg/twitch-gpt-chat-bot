"""Verify expansion counting fix"""
import sys
sys.path.insert(0, '.')

# Simulate the Zerg build with 2 hatcheries
zerg_build = [
    {'supply': 12, 'name': 'Drone', 'time': 1},
    {'supply': 13, 'name': 'Drone', 'time': 13},
    {'supply': 14, 'name': 'Overlord', 'time': 19},
    {'supply': 17, 'name': 'Hatchery', 'time': 50},  # First expansion
    {'supply': 19, 'name': 'Extractor', 'time': 70},
    {'supply': 19, 'name': 'SpawningPool', 'time': 80},
    {'supply': 19, 'name': 'Queen', 'time': 100},
    {'supply': 21, 'name': 'Zergling', 'time': 110},
    {'supply': 24, 'name': 'Queen', 'time': 130},
    {'supply': 26, 'name': 'Hatchery', 'time': 150},  # Second expansion
]

# Simulate a 1-base pattern (14 pool aggression)
one_base_pattern_early_game = [
    {'unit': 'Drone', 'time': 1, 'supply': 12},
    {'unit': 'Overlord', 'time': 19, 'supply': 14},
    {'unit': 'SpawningPool', 'time': 40, 'supply': 14},  # Very early pool
    {'unit': 'Queen', 'time': 80, 'supply': 16},
    {'unit': 'Zergling', 'time': 90, 'supply': 17},
    # No hatchery - staying on 1 base
]

expansion_names = {'hatchery', 'nexus', 'commandcenter'}

# Count expansions from new build
new_expansions = sum(1 for step in zerg_build 
                     if step.get('name', '').lower() in expansion_names)

# Count from pattern
pattern_expansions = sum(1 for step in one_base_pattern_early_game 
                         if step.get('unit', '').lower() in expansion_names)

print("=== EXPANSION COUNTING FIX TEST ===")
print(f"\nNew build (3-hatch Zerg):")
for step in zerg_build:
    marker = " <-- HATCH" if step.get('name', '').lower() in expansion_names else ""
    print(f"  {step['supply']}: {step['name']}{marker}")

print(f"\nPattern (1-base 14 pool):")
for step in one_base_pattern_early_game:
    marker = " <-- HATCH" if step.get('unit', '').lower() in expansion_names else ""
    print(f"  {step['supply']}: {step['unit']}{marker}")

print(f"\n=== RESULTS ===")
print(f"New build expansions: {new_expansions}")
print(f"Pattern expansions: {pattern_expansions}")
print(f"Difference: {abs(new_expansions - pattern_expansions)}")

if new_expansions == 2 and pattern_expansions == 0:
    print("\n✓ FIX WORKS! 2 hatcheries detected in new build, 0 in pattern.")
    print("  This would apply a HEAVY penalty (difference of 2 = 70% penalty)")
else:
    print(f"\n✗ Something wrong - expected new=2, pattern=0")



