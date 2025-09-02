#!/usr/bin/env python3

import json
from models.mathison_db import Database

def debug_grumpykitten():
    print("🔍 Debugging GrumpyKitten ML Analysis Issue")
    print("=" * 60)
    
    # 1. Check if the comment exists in database
    db = Database()
    
    print("\n1. Checking replay 20631 comment:")
    result = db.cursor.execute("SELECT Player_Comments FROM Replays WHERE ReplayId = 20631")
    replay_data = db.cursor.fetchone()
    if replay_data:
        comment = replay_data['Player_Comments']
        print(f"   Comment: '{comment}'")
    else:
        print("   No replay found!")
        return
    
    # 2. Check if pattern exists for this comment
    print("\n2. Checking if pattern exists for this comment:")
    with open('data/patterns.json', 'r') as f:
        patterns = json.load(f)
    
    found_pattern = False
    for pattern_id, pattern in patterns.items():
        if isinstance(pattern, dict) and 'comment' in pattern:
            if pattern['comment'] == comment:
                print(f"   ✅ Found pattern {pattern_id}:")
                print(f"      Comment: {pattern['comment']}")
                print(f"      Keywords: {pattern.get('keywords', [])}")
                found_pattern = True
                break
    
    if not found_pattern:
        print("   ❌ No pattern found for this exact comment!")
        print("   This suggests the learning system hasn't processed this replay yet.")
    
    # 3. Check related patterns
    print("\n3. Related patterns found:")
    related_keywords = ['cannon', 'rush', 'dt', 'dark', 'templar', 'colossus']
    for pattern_id, pattern in patterns.items():
        if isinstance(pattern, dict) and 'comment' in pattern:
            comment_lower = pattern['comment'].lower()
            if any(kw in comment_lower for kw in related_keywords):
                print(f"   Pattern {pattern_id}: {pattern['comment']}")
                print(f"      Keywords: {pattern.get('keywords', [])}")
    
    # 4. Check grumpykitten's build order for key units
    print("\n4. Analyzing GrumpyKitten's build order:")
    result = db.cursor.execute("SELECT Replay_Summary FROM Replays WHERE ReplayId = 20631")
    replay_data = db.cursor.fetchone()
    if replay_data:
        summary = replay_data['Replay_Summary']
        
        # Look for key strategic units
        strategic_units = []
        if 'Forge' in summary:
            strategic_units.append('Forge')
        if 'PhotonCannon' in summary or 'Photon Cannon' in summary:
            strategic_units.append('PhotonCannon')
        if 'DarkShrine' in summary or 'Dark Shrine' in summary:
            strategic_units.append('DarkShrine')
        if 'Dark Templar' in summary:
            strategic_units.append('Dark Templar')
        if 'Colossus' in summary:
            strategic_units.append('Colossus')
            
        print(f"   Strategic units found: {strategic_units}")
        
        # Extract build order
        if "GrumpyKitten's Build Order" in summary:
            build_section = summary.split("GrumpyKitten's Build Order")[1].split("\n\n")[0]
            build_units = []
            for line in build_section.split('\n'):
                if 'Name:' in line:
                    unit = line.split('Name: ')[1].split(',')[0].strip()
                    build_units.append(unit)
            
            print(f"   First 20 build units: {build_units[:20]}")
            
            # Check for cannon rush indicators
            early_forge = any('Forge' in unit for unit in build_units[:10])
            early_cannon = any('PhotonCannon' in unit for unit in build_units[:15])
            has_darkshrine = any('DarkShrine' in unit for unit in build_units)
            has_dt = any('Dark Templar' in unit for unit in build_units)
            
            print(f"   Early Forge (first 10): {early_forge}")
            print(f"   Early Cannon (first 15): {early_cannon}")  
            print(f"   Has DarkShrine: {has_darkshrine}")
            print(f"   Has Dark Templar: {has_dt}")

if __name__ == "__main__":
    debug_grumpykitten()
