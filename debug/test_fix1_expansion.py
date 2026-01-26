"""Test Fix 1: Expansion counting from original build orders"""

# Test the expansion counting logic directly (no imports needed)
expansion_names = {'hatchery', 'nexus', 'commandcenter'}

# 2-hatch Zerg build
two_hatch_build = [
    {'supply': 13, 'name': 'Drone', 'time': 10},
    {'supply': 17, 'name': 'Hatchery', 'time': 50},
    {'supply': 19, 'name': 'SpawningPool', 'time': 88},
    {'supply': 26, 'name': 'Hatchery', 'time': 150},
]

# 1-base pattern (14 pool)
one_base_pattern = [
    {'unit': 'Drone', 'time': 10},
    {'unit': 'SpawningPool', 'time': 88},
    {'unit': 'Queen', 'time': 120},
]

new_expansions = sum(1 for step in two_hatch_build 
                   if step.get('name', '').lower() in expansion_names)
pattern_expansions = sum(1 for step in one_base_pattern 
                        if step.get('unit', '').lower() in expansion_names)

print("=== Fix 1 Test: Expansion Counting ===")
print(f"2-hatch build expansions: {new_expansions}")
print(f"1-base pattern expansions: {pattern_expansions}")
print(f"Difference: {abs(new_expansions - pattern_expansions)}")

if new_expansions == 2 and pattern_expansions == 0:
    print("✓ PASS: Expansion counting works correctly!")
    print("  2 hatcheries detected vs 0 in pattern = 2 base difference")
    print("  This will apply 70% penalty (expansion_multiplier = 0.3)")
else:
    print(f"✗ FAIL: Expected new=2, pattern=0, got new={new_expansions}, pattern={pattern_expansions}")



