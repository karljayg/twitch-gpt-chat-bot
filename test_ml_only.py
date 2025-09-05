#!/usr/bin/env python3
"""
Simple test script for ML analysis only - bypasses chat system imports
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

def test_ml_analysis_only():
    """Test ML analysis without chat system dependencies"""
    print("🧪 Testing ML Analysis (ML only)")
    print("=" * 60)
    
    try:
        # Create analyzer instance, mock logger, and database connection
        analyzer = MLOpponentAnalyzer()
        logger = MockLogger()
        db = Database()
        
        # Test the analysis
        result = analyzer.analyze_opponent_for_chat(
            opponent_name="grumpykitten",
            opponent_race="protoss",
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

if __name__ == "__main__":
    test_ml_analysis_only()
