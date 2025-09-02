#!/usr/bin/env python3

from models.mathison_db import Database
from load_learning_data import LearningDataRegenerator

def test_single_replay():
    print("🔍 Testing Single Replay 20631 Processing")
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
    
    # Test the learning data regenerator logic
    regenerator = LearningDataRegenerator()
    
    print("\n🔍 Testing create_game_data_from_replay...")
    game_data = regenerator.create_game_data_from_replay(replay)
    
    if game_data:
        print("✅ Game data created successfully!")
        print(f"   Opponent: {game_data['opponent_name']} ({game_data['opponent_race']})")
        print(f"   Result: {game_data['result']}")
        print(f"   Is about opponent: {game_data['is_about_opponent']}")
        print(f"   Build order steps: {len(game_data.get('build_order', []))}")
        
        # Show first few build steps
        build_order = game_data.get('build_order', [])
        if build_order:
            print("\n📋 First 10 build steps from regenerator:")
            for i, step in enumerate(build_order[:10]):
                time_str = f"{step['time']//60}:{step['time']%60:02d}"
                print(f"  {i+1}. {time_str} - {step['name']} (Supply: {step['supply']})")
        else:
            print("❌ No build order extracted!")
    else:
        print("❌ Failed to create game data!")

if __name__ == "__main__":
    test_single_replay()
