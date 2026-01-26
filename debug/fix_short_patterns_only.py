#!/usr/bin/env python3
"""
TARGETED FIX: Only update patterns with short/missing build orders.
Does NOT touch patterns that already have good data.

This script:
1. Identifies patterns with < 20 items in their signature
2. Fetches the corresponding replay from database
3. Extracts the OPPONENT's build order (always - since comments describe opponent strategies)
4. Updates ONLY those patterns, leaving good patterns untouched
"""

import sys
import os
import json
import re
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.mathison_db import Database
from adapters.database.database_client_factory import create_database_client
from settings import config

def extract_build_order_from_summary(replay_summary, player_name):
    """Extract build order data from replay summary for a specific player"""
    try:
        build_order = []
        
        patterns = [
            rf"{re.escape(player_name)}'s Build Order.*?:\n(.*?)(?:\n\n[A-Z][a-zA-Z]+.*?'s Build Order)",
            rf"{re.escape(player_name)}'s Build Order.*?:\n(.*?)(?:\n\n(?!Time:)[A-Z][a-zA-Z]+)",
            rf"{re.escape(player_name)}'s Build Order.*?:\n(.*?)(?:\n\n|$)",
        ]
        
        build_match = None
        for pattern in patterns:
            build_match = re.search(pattern, replay_summary, re.DOTALL | re.IGNORECASE)
            if build_match:
                break
        
        if build_match:
            build_text = build_match.group(1)
            step_pattern = r"Time: (\d+):(\d+), Name: ([^,]+), Supply: (\d+)"
            steps = re.findall(step_pattern, build_text)
            
            for minute, second, unit_name, supply in steps:
                time_seconds = int(minute) * 60 + int(second)
                build_order.append({
                    'supply': int(supply),
                    'name': unit_name.strip(),
                    'time': time_seconds
                })
        
        return build_order
        
    except Exception as e:
        print(f"    Error: {e}")
        return []

def main():
    print("=" * 70)
    print("TARGETED FIX: Only updating patterns with short build orders")
    print("=" * 70)
    
    # Load patterns
    with open('data/patterns.json', 'r', encoding='utf-8') as f:
        patterns = json.load(f)
    
    # Load comments
    with open('data/comments.json', 'r', encoding='utf-8') as f:
        comments_data = json.load(f)
    
    # Create comment lookup by matching text
    comment_lookup = {}
    for c in comments_data.get('comments', []):
        comment_lookup[c.get('comment', '')] = c
        comment_lookup[c.get('raw_comment', '')] = c
    
    # Find patterns with short build orders
    short_patterns = []
    for name, pat in patterns.items():
        sig = pat.get('signature', {})
        early_game = sig.get('early_game', [])
        if len(early_game) < 20:  # Threshold for "short" pattern
            short_patterns.append((name, pat, len(early_game)))
    
    print(f"\nFound {len(short_patterns)} patterns with < 20 items in signature")
    print(f"(Out of {len(patterns)} total patterns)")
    
    if not short_patterns:
        print("\nNo short patterns to fix!")
        return
    
    # Connect to database
    db = create_database_client()
    
    # Process each short pattern
    fixed = 0
    skipped = 0
    errors = 0
    
    for name, pat, item_count in short_patterns:
        comment_text = pat.get('comment', '')
        race = pat.get('race', '').lower()
        
        print(f"\n{name}: '{comment_text[:50]}...' ({item_count} items)")
        
        # Find matching comment to get opponent info
        matching_comment = comment_lookup.get(comment_text)
        if not matching_comment:
            print(f"  [!] No matching comment found, skipping")
            skipped += 1
            continue
        
        game_data = matching_comment.get('game_data', {})
        opponent_name = game_data.get('opponent_name', '')
        opponent_race = game_data.get('opponent_race', '')
        
        if not opponent_name:
            print(f"  [!] No opponent name in game_data, skipping")
            skipped += 1
            continue
        
        # Find the replay in database by opponent name and date
        game_date = game_data.get('date', '')
        try:
            cursor = db.connection.cursor(dictionary=True)
            query = """
            SELECT ReplayId, Replay_Summary 
            FROM Replays 
            WHERE Player_Comments = %s
            LIMIT 1
            """
            cursor.execute(query, (comment_text,))
            result = cursor.fetchone()
            cursor.close()
            
            if not result:
                print(f"  [!] No replay found in database, skipping")
                skipped += 1
                continue
            
            replay_summary = result['Replay_Summary']
            
            # ALWAYS extract opponent's build order (comments describe opponent strategies)
            build_order = extract_build_order_from_summary(replay_summary, opponent_name)
            
            if len(build_order) < 20:
                print(f"  [!] Extracted build order still short ({len(build_order)} steps), skipping")
                skipped += 1
                continue
            
            # Update the pattern signature
            new_early_game = []
            for i, step in enumerate(build_order[:120]):  # First 120 steps
                new_early_game.append({
                    'unit': step['name'],
                    'count': 1,
                    'order': i + 1,
                    'supply': step['supply'],
                    'time': step['time']
                })
            
            patterns[name]['signature']['early_game'] = new_early_game
            
            # Also update key_timings with strategic buildings
            key_timings = {}
            strategic_buildings = {'spawningpool', 'hatchery', 'roachwarren', 'banelingnest', 
                                   'spire', 'hydraliskden', 'barracks', 'factory', 'starport',
                                   'gateway', 'cyberneticscore', 'stargate', 'roboticsfacility'}
            for step in build_order:
                name_lower = step['name'].lower()
                if name_lower in strategic_buildings and name_lower not in key_timings:
                    key_timings[step['name']] = step['time']
            patterns[name]['signature']['key_timings'] = key_timings
            
            print(f"  [OK] Updated: {item_count} -> {len(new_early_game)} items")
            fixed += 1
            
        except Exception as e:
            print(f"  [X] Error: {e}")
            errors += 1
    
    # Save updated patterns
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Fixed: {fixed}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")
    
    if fixed > 0:
        # Backup before saving
        backup_path = f"data/patterns_before_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(patterns, f, indent=2)
        print(f"\nBackup saved to: {backup_path}")
        
        # Save
        with open('data/patterns.json', 'w', encoding='utf-8') as f:
            json.dump(patterns, f, indent=2)
        print(f"Updated patterns.json")
    else:
        print("\nNo changes made")

if __name__ == "__main__":
    main()



