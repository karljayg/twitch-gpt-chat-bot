#!/usr/bin/env python3

import sys
import os
import json
sys.path.append('.')

from api.pattern_learning import SC2PatternLearner
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Mock database
class MockDB:
    def update_player_comments_in_last_replay(self, comment):
        return True

def parse_build_order_from_summary(summary_text):
    """Parse build order from the replay summary text"""
    build_data = []
    in_build_order = False
    current_player = None
    
    for line in summary_text.split('\n'):
        line = line.strip()
        if "Build Order (first set of steps):" in line:
            in_build_order = True
            current_player = line.split("'s")[0]
            continue
        elif in_build_order and line.startswith("Time:"):
            # Parse: "Time: 0:00, Name: Probe, Supply: 12"
            try:
                parts = line.split(", ")
                time_part = parts[0].split(": ")[1]  # "0:00"
                name_part = parts[1].split(": ")[1]  # "Probe"
                supply_part = parts[2].split(": ")[1]  # "12"
                
                # Convert time to seconds
                minutes, seconds = map(int, time_part.split(":"))
                time_seconds = minutes * 60 + seconds
                
                build_data.append({
                    'supply': int(supply_part),
                    'name': name_part,
                    'time': time_seconds
                })
            except Exception as e:
                logger.debug(f"Could not parse build order line: {line} - {e}")
                continue
        elif in_build_order and not line.startswith("Time:"):
            # End of build order section
            break
    
    return build_data

def test_with_real_replay():
    """Test the pattern learning system with real replay data"""
    db = MockDB()
    learner = SC2PatternLearner(db, logger)
    
    # Read the real replay summary
    with open('temp/replay_summary.txt', 'r') as f:
        replay_summary = f.read()
    
    # Parse build order from summary
    build_data = parse_build_order_from_summary(replay_summary)
    logger.info(f"Parsed {len(build_data)} build order steps")
    
    # Create game data similar to what the bot would create
    game_data = {
        'opponent_name': 'BurnerAcct',
        'opponent_race': 'Zerg',
        'result': 'Victory',
        'map': 'Incorporeal LE',
        'duration': '20m 9s',
        'date': '2025-08-29 21:50:31',
        'build_order': build_data
    }
    
    # Test comment processing
    test_comment = "gateway expand to stalker pressure with blink upgrade"
    logger.info(f"Processing comment: {test_comment}")
    
    # Process the comment
    learner._process_new_comment(game_data, test_comment)
    
    # Check what was created
    logger.info("Pattern learning completed. Check data/ folder for results.")
    
    # Show what patterns were created
    if learner.patterns:
        logger.info(f"Created {sum(len(p) for p in learner.patterns.values())} patterns")
        for keyword, patterns in learner.patterns.items():
            logger.info(f"Keyword '{keyword}': {len(patterns)} patterns")
    else:
        logger.info("No patterns created")

if __name__ == "__main__":
    test_with_real_replay()
