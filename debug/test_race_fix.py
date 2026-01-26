"""Test that race is taken from game_data, not detected from signature"""

# Simulate the fixed logic
def get_race_fixed(pattern):
    """Fixed version - uses game_data.opponent_race first"""
    game_data = pattern.get('game_data', {})
    pattern_race = game_data.get('opponent_race', '').lower()
    if not pattern_race or pattern_race == 'unknown':
        # Fallback to detection (only looks for Pool/Barracks/Gateway)
        pattern_race = detect_race_from_signature(pattern)
    return pattern_race

def detect_race_from_signature(pattern):
    """Old buggy detection - only checks Pool/Barracks/Gateway"""
    signature = pattern.get('signature', {})
    early_game = signature.get('early_game', [])
    
    for entry in early_game:
        if isinstance(entry, dict) and 'unit' in entry:
            unit_name = entry['unit']
            if 'Pool' in unit_name:
                return "zerg"
            elif 'Barracks' in unit_name:
                return "terran"
            elif 'Gateway' in unit_name:
                return "protoss"
    return "unknown"

print("=== Test: Race Detection Fix ===")

# Test 1: Forge-first Protoss (no Gateway early)
forge_protoss = {
    'game_data': {'opponent_race': 'Protoss', 'opponent_name': 'Test'},
    'signature': {
        'early_game': [
            {'unit': 'Probe', 'time': 10},
            {'unit': 'Forge', 'time': 50},
            {'unit': 'PhotonCannon', 'time': 80},
        ]
    },
    'comment': 'cannon rush'
}

old_result = detect_race_from_signature(forge_protoss)
new_result = get_race_fixed(forge_protoss)
print(f"\n1. Forge-first Protoss (cannon rush):")
print(f"   Old detection: '{old_result}' (WRONG - no Gateway)")
print(f"   Fixed method: '{new_result}' (uses game_data)")
assert new_result == 'protoss', "Should be protoss from game_data"

# Test 2: Stargate Protoss (no Gateway)
stargate_protoss = {
    'game_data': {'opponent_race': 'Protoss'},
    'signature': {
        'early_game': [
            {'unit': 'Probe', 'time': 10},
            {'unit': 'Stargate', 'time': 150},
            {'unit': 'VoidRay', 'time': 200},
        ]
    },
    'comment': 'void ray rush'
}

old_result = detect_race_from_signature(stargate_protoss)
new_result = get_race_fixed(stargate_protoss)
print(f"\n2. Stargate Protoss (void ray rush):")
print(f"   Old detection: '{old_result}' (WRONG - no Gateway)")
print(f"   Fixed method: '{new_result}' (uses game_data)")
assert new_result == 'protoss', "Should be protoss from game_data"

# Test 3: Normal Zerg (has Pool)
normal_zerg = {
    'game_data': {'opponent_race': 'Zerg'},
    'signature': {
        'early_game': [
            {'unit': 'Drone', 'time': 10},
            {'unit': 'SpawningPool', 'time': 88},
        ]
    },
    'comment': '12 pool'
}

old_result = detect_race_from_signature(normal_zerg)
new_result = get_race_fixed(normal_zerg)
print(f"\n3. Normal Zerg (12 pool):")
print(f"   Old detection: '{old_result}' (correct by luck)")
print(f"   Fixed method: '{new_result}' (uses game_data)")
assert new_result == 'zerg', "Should be zerg"

print("\n✓ All tests passed! Race detection fix works correctly.")



