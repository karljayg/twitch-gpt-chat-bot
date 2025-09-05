#!/usr/bin/env python3

from models.mathison_db import Database
from load_learning_data import LearningDataRegenerator

def debug_replay_20631():
    print("🔍 Debugging Replay 20631 Processing")
    print("=" * 50)
    
    # Get replay 20631 from database
    db = Database()
    result = db.cursor.execute('''
        SELECT * FROM Replays WHERE ReplayId = 20631
    ''')
    replay = db.cursor.fetchone()
    
    if not replay:
        print("❌ Replay 20631 not found!")
        return
    
    print(f"✅ Found replay 20631")
    print(f"   Player_Comments: {replay['Player_Comments']}")
    print(f"   Date_Played: {replay['Date_Played']}")
    
    # Test the parsing logic
    regenerator = LearningDataRegenerator()
    
    print("\n🔍 Testing player name parsing...")
    parsed_data = regenerator.extract_player_names_from_summary(replay['Replay_Summary'])
    print(f"   Parsing success: {parsed_data['parsing_success']}")
    print(f"   Player1: {parsed_data['player1_name']} ({parsed_data['player1_race']})")
    print(f"   Player2: {parsed_data['player2_name']} ({parsed_data['player2_race']})")
    
    if parsed_data.get('error'):
        print(f"   Error: {parsed_data['error']}")
    
    print("\n🔍 Testing game data creation...")
    game_data = regenerator.create_game_data_from_replay(replay)
    
    if game_data:
        print("✅ Game data created successfully!")
        print(f"   Opponent: {game_data['opponent_name']} ({game_data['opponent_race']})")
        print(f"   Result: {game_data['result']}")
        print(f"   Build order steps: {len(game_data.get('build_order', []))}")
    else:
        print("❌ Failed to create game data!")
    
    # Show GrumpyKitten's build order section specifically
    print("\n📄 Looking for GrumpyKitten's Build Order section...")
    
    import re
    summary = replay['Replay_Summary']
    
    # Look for GrumpyKitten's build order section
    pattern = r"GrumpyKitten's Build Order.*?:\n(.*?)(?:\n\n|\nKJ's Build Order)"
    build_match = re.search(pattern, summary, re.DOTALL | re.IGNORECASE)
    
    if build_match:
        build_text = build_match.group(1)
        print("✅ Found GrumpyKitten's build order section:")
        print(build_text[:1000])  # Show first 1000 chars
        
        # Count the steps
        step_pattern = r"Time: (\d+):(\d+), Name: ([^,]+), Supply: (\d+)"
        steps = re.findall(step_pattern, build_text)
        print(f"\n🔢 Total build steps found: {len(steps)}")
        
        if steps:
            print("📋 First 10 steps:")
            for i, (minute, second, unit_name, supply) in enumerate(steps[:10]):
                print(f"  {i+1}. {minute}:{int(second):02d} - {unit_name.strip()} (Supply: {supply})")
    else:
        print("❌ Could not find GrumpyKitten's build order section")
        print("📄 Replay Summary (first 1000 chars):")
        print(summary[:1000])

if __name__ == "__main__":
    debug_replay_20631()
