#!/usr/bin/env python3
"""
Test script for ML opponent analysis
Usage: python analyze_player.py <opponent_name> <opponent_race> [map_name]
Example: python analyze_player.py grumpykitten protoss "Ancient Cistern LE"
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.ml_opponent_analyzer import MLOpponentAnalyzer
from models.mathison_db import Database

class MockLogger:
    """Mock logger for testing purposes"""
    def debug(self, msg): print(f"[DEBUG] {msg}")
    def info(self, msg): print(f"[INFO] {msg}")
    def warning(self, msg): print(f"[WARN] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")

def test_ml_analysis_for_opponent(opponent_name, opponent_race, current_map="Unknown Map"):
    """Test ML analysis for a specific opponent"""
    print(f"🧪 Testing ML Analysis for: {opponent_name} ({opponent_race}) on {current_map}")
    print("=" * 60)
    
    try:
        # Create analyzer instance, mock logger, and database connection
        analyzer = MLOpponentAnalyzer()
        logger = MockLogger()
        db = Database()
        
        # Test the analysis
        result = analyzer.analyze_opponent_for_chat(
            opponent_name=opponent_name,
            opponent_race=opponent_race,
            current_map=current_map,
            logger=logger,
            db=db
        )
        
        if result:
            print("✅ ML Analysis Generated:")
            print(f"📝 Raw Data: {result}")
            
            # Show the top 3 concise summaries that would appear in Twitch chat
            if result.get('matched_patterns'):
                print(f"\n🎯 TOP 3 TWITCH CHAT SUMMARIES:")
                for i, pattern in enumerate(result['matched_patterns'][:3]):
                    similarity_pct = pattern['similarity'] * 100
                    print(f"💬 #{i+1} ({similarity_pct:.1f}% match): {pattern['comment']}")
            elif result.get('summary'):
                print(f"\n🎯 TWITCH CHAT SUMMARY:")
                print(f"💬 {result['summary']}")
            else:
                print(f"\n🎯 TWITCH CHAT SUMMARY:")
                print(f"💬 ML Analysis: {result.get('opponent_name', 'Unknown')} ({result.get('opponent_race', 'Unknown')}) - Analysis available")
        else:
            print("❌ No ML Analysis generated")
            
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

def test_multiple_opponents():
    """Test ML analysis for multiple known opponents"""
    test_cases = [
        ("grumpykitten", "protoss", "Ancient Cistern LE"),
        ("joebobjoe", "protoss", "Royal Blood LE"),
        ("theblob", "protoss", "Royal Blood LE"),
        ("markus", "protoss", "Royal Blood LE"),
        ("braveboy", "zerg", "Royal Blood LE"),
    ]
    
    for opponent_name, opponent_race, current_map in test_cases:
        print(f"\n{'='*60}")
        test_ml_analysis_for_opponent(opponent_name, opponent_race, current_map)
        print(f"{'='*60}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_player.py <opponent_name> <opponent_race> [map_name]")
        print("Example: python analyze_player.py grumpykitten protoss")
        print("\nOr run without arguments to test multiple opponents:")
        print("python analyze_player.py all")
        sys.exit(1)
    
    opponent_name = sys.argv[1]
    
    if opponent_name.lower() == "all":
        test_multiple_opponents()
    else:
        if len(sys.argv) < 3:
            print("Usage: python analyze_player.py <opponent_name> <opponent_race> [map_name]")
            print("Example: python analyze_player.py grumpykitten protoss")
            sys.exit(1)
        
        opponent_race = sys.argv[2]
        current_map = sys.argv[3] if len(sys.argv) > 3 else "Unknown Map"
        test_ml_analysis_for_opponent(opponent_name, opponent_race, current_map)
