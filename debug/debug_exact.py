"""Debug exact matching - simulate bot behavior"""
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

# Exactly as in ml_opponent_analyzer.py lines 477-519
def extract_strategic_items_from_build(build_order, opponent_race):
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

# Exactly as in ml_opponent_analyzer.py lines 550-616
def extract_strategic_items_from_signature(signature, race):
    strategic_item_names = get_strategic_item_names(race)
    seen_items = {}
    
    if 'early_game' in signature:
        for i, step in enumerate(signature['early_game']):
            unit_name = step.get('unit', '').lower()  # Uses 'unit' key!
            timing = step.get('time', 0)
            
            if unit_name in strategic_item_names and unit_name not in seen_items:
                seen_items[unit_name] = {
                    'name': unit_name,
                    'timing': timing,
                    'position': i
                }
    
    return list(seen_items.values())

# Load the comment
with open('data/comments.json', 'r') as f:
    comments = json.load(f)

for c in comments['comments']:
    if '1 base reaper bunker' in c.get('comment', '').lower():
        stored_bo = c['game_data'].get('build_order', [])
        
        print("=== SIMULATING match_build_against_all_patterns ===")
        print(f"\nStored build order: {len(stored_bo)} steps")
        
        # Step 1: match_build_against_all_patterns converts stored_bo to signature
        # Lines 106-114 in ml_opponent_analyzer.py
        early_game_signature = []
        for i, step in enumerate(stored_bo):
            early_game_signature.append({
                'unit': step.get('name', ''),  # 'name' -> 'unit'
                'time': step.get('time', 0),
                'supply': step.get('supply', 0),
                'count': 1,
                'order': i + 1
            })
        
        pattern_signature = {'early_game': early_game_signature}
        
        # Step 2: _match_build_against_patterns calls extract on both sides
        # Pattern side: _extract_strategic_items_from_signature (uses 'unit' key)
        pattern_items = extract_strategic_items_from_signature(pattern_signature, 'Terran')
        
        # New build side: _extract_strategic_items_from_build (uses 'name' key)
        # In the bot, "new build" is game_data['build_order'] from replay_data
        # If this is the SAME game, it should have the SAME data
        new_build_items = extract_strategic_items_from_build(stored_bo, 'Terran')
        
        print(f"\nPattern items (from signature): {len(pattern_items)}")
        for item in sorted(pattern_items, key=lambda x: x['timing']):
            print(f"  {item['name']} @ {item['timing']}s")
        
        print(f"\nNew build items (from build_order): {len(new_build_items)}")
        for item in sorted(new_build_items, key=lambda x: x['timing']):
            print(f"  {item['name']} @ {item['timing']}s")
        
        # Are they identical?
        pattern_set = {(item['name'], item['timing']) for item in pattern_items}
        new_set = {(item['name'], item['timing']) for item in new_build_items}
        
        if pattern_set == new_set:
            print("\n✓ Items are IDENTICAL - should match 100%")
        else:
            print(f"\n✗ Items DIFFER!")
            print(f"  In pattern but not new: {pattern_set - new_set}")
            print(f"  In new but not pattern: {new_set - pattern_set}")
        
        break



