#!/usr/bin/env python3

import sys
import os
sys.path.append('.')

from api.pattern_learning import SC2PatternLearner
from models.mathison_db import Database
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock database
class MockDB:
    def update_player_comments_in_last_replay(self, comment):
        return True
    
    def get_player_comments(self, player_name, player_race):
        return []

# Test the new structure
def test_new_structure():
    db = MockDB()
    learner = SC2PatternLearner(db, logger)
    
    # Test data
    test_game_data = {
        'opponent_name': 'TestPlayer',
        'opponent_race': 'protoss',
        'result': 'Victory',
        'map': 'TestMap',
        'duration': '20m 30s',
        'date': '2025-08-29 18:00:00',
        'build_order': [
            {'name': 'Gateway', 'supply': 10, 'time': 30},
            {'name': 'CyberneticsCore', 'supply': 15, 'time': 80},
            {'name': 'Stalker', 'supply': 20, 'time': 120}
        ]
    }
    
    # Process a comment
    test_comment = "gateway expand to stalker pressure"
    learner._process_new_comment(test_game_data, test_comment)
    
    print("✅ Test completed. Check data/ folder for new structure.")

if __name__ == "__main__":
    test_new_structure()
