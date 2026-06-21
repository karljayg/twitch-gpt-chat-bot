"""
Test script to verify database query optimization
This should show only 1 API call instead of 3
"""
import logging
import sys
from adapters.database.database_client_factory import create_database_client
from api.ml_opponent_analyzer import get_ml_analyzer

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s'
)
logger = logging.getLogger("test")

def test_optimization():
    """Test that opponent_record is reused correctly"""
    print("\n=== Testing Database Query Optimization ===\n")
    
    db = create_database_client()
    analyzer = get_ml_analyzer()
    
    test_opponent = "Atlantis"
    test_race = "Protoss"
    
    print(f"Testing with opponent: {test_opponent} ({test_race})")
    print("\n1. Querying database once (simulating _display_pattern_validation first check)...")
    
    # First check - this is the ONLY database query that should happen
    opponent_record = db.check_player_and_race_exists(test_opponent, test_race)
    
    if not opponent_record:
        print(f"\n[ERROR] Player {test_opponent} not found in database")
        print("This test requires an existing player. Try a different name.")
        return
    
    print(f"✓ Found player: {test_opponent} (Id: {opponent_record.get('Player1_Id', 'unknown')})")
    
    print("\n2. Calling analyze_opponent_for_chat WITH opponent_record (should use cached data)...")
    
    # This should NOT query the database again - it should use opponent_record
    analysis_data = analyzer.analyze_opponent_for_chat(
        test_opponent, test_race, logger, db, opponent_record
    )
    
    if analysis_data:
        print(f"✓ ML analysis completed using cached data")
        print(f"   Matched {len(analysis_data.get('matched_patterns', []))} patterns")
    else:
        print("  No ML analysis data (opponent may not have sufficient history)")
    
    print("\n3. Verification:")
    print("   Check the logs above. You should see:")
    print("   - ONE 'Player and race exists' log (the initial query)")
    print("   - 'ML Analysis: Using cached player data' log (reusing the data)")
    print("   - NO additional 'Player and race exists' logs")
    
    print("\n=== Test Complete ===")
    print("\nBefore optimization: Would see 3 'Player and race exists' logs")
    print("After optimization:  Should see 1 'Player and race exists' log + 1 'Using cached' log")

if __name__ == "__main__":
    try:
        test_optimization()
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
