"""Debug the actual matching between current game and stored pattern"""
import json
import sys
sys.path.insert(0, '.')

from settings import config

def get_strategic_item_names(race):
    strategic_items = set()
    if race in config.SC2_STRATEGIC_ITEMS:
        race_items = config.SC2_STRATEGIC_ITEMS[race]
        for category in ['buildings', 'units', 'upgrades']:
            if category in race_items:
                items = [item.strip().lower() for item in race_items[category].split(',')]
                strategic_items.update(items)
    return strategic_items

def extract_strategic_items_from_build(build_order, opponent_race):
    """Same as ml_opponent_analyzer._extract_strategic_items_from_build"""
    non_strategic = {
        'probe', 'scv', 'drone', 'mule',
        'pylon', 'supplydepot', 'overlord', 'overseer',
        'nexus', 'commandcenter', 'hatchery', 'lair', 'hive',
        'orbitalcommand', 'planetaryfortress'
    }
    
    strategic_items = get_strategic_item_names(opponent_race)
    
    seen_items = {}
    for i, step in enumerate(build_order):
        name = step.get('name', '').lower()
        timing = step.get('time', 0)
        
        if name in non_strategic:
            continue
        
        if name in strategic_items and name not in seen_items:
            seen_items[name] = {
                'name': name,
                'timing': timing,
                'position': i,
            }
    
    return list(seen_items.values())

def extract_strategic_items_from_signature(signature, race):
    """Same as ml_opponent_analyzer._extract_strategic_items_from_signature"""
    strategic_item_names = get_strategic_item_names(race)
    seen_items = {}
    
    if 'early_game' in signature:
        for i, step in enumerate(signature['early_game']):
            unit_name = step.get('unit', '').lower()
            timing = step.get('time', 0)
            
            if unit_name in strategic_item_names and unit_name not in seen_items:
                seen_items[unit_name] = {
                    'name': unit_name,
                    'timing': timing,
                    'position': i
                }
    
    return list(seen_items.values())

def compare_build_signatures(new_build_items, pattern_items, race):
    """Same as ml_opponent_analyzer._compare_build_signatures - with debug prints"""
    if not new_build_items or not pattern_items:
        return 0.0
    
    new_build_dict = {item['name']: item for item in new_build_items}
    pattern_dict = {item['name']: item for item in pattern_items}
    
    matching_items = set(new_build_dict.keys()) & set(pattern_dict.keys())
    
    print(f"\n=== COMPARISON DEBUG ===")
    print(f"New build items: {set(new_build_dict.keys())}")
    print(f"Pattern items: {set(pattern_dict.keys())}")
    print(f"Matching items: {matching_items}")
    
    if not matching_items:
        return 0.0
    
    tech_buildings = {
        'banelingnest', 'roachwarren', 'spire', 'hydraliskden', 'lurkerden',
        'infestationpit', 'ultraliskcavern', 'nydusnetwork',
        'stargate', 'roboticsfacility', 'darkshrine', 'templararchive', 'fleetbeacon',
        'factory', 'starport', 'fusioncore', 'ghostacademy'
    }
    
    # DIRECTION 1: Pattern -> New Build
    pattern_total_weight = 0.0
    pattern_matched_weight = 0.0
    
    print(f"\n--- Direction 1: Pattern -> New Build ---")
    for item_name, item_data in pattern_dict.items():
        timing = item_data['timing']
        is_tech = item_name in tech_buildings
        
        if timing < 300:
            weight = 4.0 if is_tech else 3.0
        elif timing < 480:
            weight = 3.0 if is_tech else 2.0
        else:
            weight = 2.0 if is_tech else 1.0
        
        pattern_total_weight += weight
        
        if item_name in matching_items:
            new_timing = new_build_dict[item_name]['timing']
            timing_diff = abs(new_timing - timing)
            if timing_diff < 30:
                timing_bonus = 1.0
            elif timing_diff < 60:
                timing_bonus = 0.8
            elif timing_diff < 120:
                timing_bonus = 0.5
            else:
                timing_bonus = 0.3
            
            pattern_matched_weight += weight * timing_bonus
            print(f"  {item_name}: pattern={timing}s, new={new_timing}s, diff={timing_diff}s, bonus={timing_bonus}, weight={weight}")
        else:
            print(f"  {item_name}: NOT IN NEW BUILD, weight={weight}")
    
    # DIRECTION 2: New Build -> Pattern
    new_total_weight = 0.0
    new_matched_weight = 0.0
    
    print(f"\n--- Direction 2: New Build -> Pattern ---")
    for item_name, item_data in new_build_dict.items():
        timing = item_data['timing']
        is_tech = item_name in tech_buildings
        
        if timing < 300:
            weight = 4.0 if is_tech else 3.0
        elif timing < 480:
            weight = 3.0 if is_tech else 2.0
        else:
            weight = 2.0 if is_tech else 1.0
        
        new_total_weight += weight
        
        if item_name in matching_items:
            pattern_timing = pattern_dict[item_name]['timing']
            timing_diff = abs(timing - pattern_timing)
            if timing_diff < 30:
                timing_bonus = 1.0
            elif timing_diff < 60:
                timing_bonus = 0.8
            elif timing_diff < 120:
                timing_bonus = 0.5
            else:
                timing_bonus = 0.3
            
            new_matched_weight += weight * timing_bonus
            print(f"  {item_name}: new={timing}s, pattern={pattern_timing}s, diff={timing_diff}s, bonus={timing_bonus}, weight={weight}")
        else:
            print(f"  {item_name}: NOT IN PATTERN, weight={weight}")
    
    pattern_similarity = pattern_matched_weight / pattern_total_weight if pattern_total_weight > 0 else 0.0
    new_similarity = new_matched_weight / new_total_weight if new_total_weight > 0 else 0.0
    
    print(f"\n--- Similarity Calculation ---")
    print(f"Pattern matched: {pattern_matched_weight}/{pattern_total_weight} = {pattern_similarity:.2%}")
    print(f"New matched: {new_matched_weight}/{new_total_weight} = {new_similarity:.2%}")
    
    if pattern_similarity > 0 and new_similarity > 0:
        similarity = 2 * (pattern_similarity * new_similarity) / (pattern_similarity + new_similarity)
    else:
        similarity = 0.0
    
    print(f"Harmonic mean: {similarity:.2%}")
    
    # Critical tech penalty
    critical_tech = {
        'forge', 'stargate', 'roboticsfacility', 'darkshrine', 'templararchive', 'fleetbeacon',
        'roachwarren', 'banelingnest', 'spire', 'hydraliskden', 'infestationpit', 'ultraliskcavern', 'lurkerden',
        'factory', 'starport', 'ghostacademy', 'fusioncore'
    }
    
    pattern_critical = set(item for item in pattern_dict.keys() if item in critical_tech)
    new_critical = set(item for item in new_build_dict.keys() if item in critical_tech)
    missing_critical = pattern_critical - new_critical
    
    print(f"\n--- Critical Tech ---")
    print(f"Pattern critical: {pattern_critical}")
    print(f"New critical: {new_critical}")
    print(f"Missing: {missing_critical}")
    
    if missing_critical and similarity > 0:
        matching_critical_count = len(pattern_critical & new_critical)
        total_critical_count = len(pattern_critical)
        
        if total_critical_count > 0:
            critical_ratio = matching_critical_count / total_critical_count
            if critical_ratio < 0.5:
                critical_penalty = critical_ratio * 0.4
            else:
                critical_penalty = 0.2 + (critical_ratio - 0.5) * 1.6
            
            print(f"Critical ratio: {matching_critical_count}/{total_critical_count} = {critical_ratio:.2%}")
            print(f"Critical penalty multiplier: {critical_penalty:.2%}")
            similarity *= critical_penalty
    
    print(f"\n=== FINAL SIMILARITY: {similarity:.2%} ===")
    return similarity


# Load comments.json
with open('data/comments.json', 'r') as f:
    d = json.load(f)

# Find the target comment
target_comment = None
for c in d['comments']:
    if '1 base reaper bunker' in c.get('comment', '').lower():
        target_comment = c
        break

if not target_comment:
    print("Comment not found!")
    sys.exit(1)

stored_bo = target_comment['game_data'].get('build_order', [])
print(f"Comment: {target_comment['comment']}")
print(f"Stored build order has {len(stored_bo)} steps")

# The "new build" from the current game is the SAME as stored (should be 100%)
# But in match_build_against_all_patterns, the pattern is created from stored_bo
# and the new build is the current game's build order

# Simulate what the code does:
# 1. Pattern signature created from stored_bo
early_game_signature = []
for i, step in enumerate(stored_bo):
    early_game_signature.append({
        'unit': step.get('name', ''),
        'time': step.get('time', 0),
        'supply': step.get('supply', 0),
        'count': 1,
        'order': i + 1
    })

pattern_signature = {'early_game': early_game_signature}

# 2. Extract items from pattern (what the code does)
pattern_items = extract_strategic_items_from_signature(pattern_signature, 'Terran')
print(f"\nPattern strategic items ({len(pattern_items)}):")
for item in pattern_items:
    print(f"  {item['name']} @ {item['timing']}s")

# 3. Extract items from "new build" (same build order - should match 100%)
new_build_items = extract_strategic_items_from_build(stored_bo, 'Terran')
print(f"\nNew build strategic items ({len(new_build_items)}):")
for item in new_build_items:
    print(f"  {item['name']} @ {item['timing']}s")

# 4. Compare
similarity = compare_build_signatures(new_build_items, pattern_items, 'Terran')



