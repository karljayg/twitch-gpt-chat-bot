#!/usr/bin/env python3

import sys
import os
import json
import tempfile
import shutil
sys.path.append('.')

from api.pattern_learning import SC2PatternLearner
import logging
import unittest

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestPatternLearningImprovements(unittest.TestCase):
    """Test suite for improved pattern learning system"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary data directory
        self.test_data_dir = tempfile.mkdtemp()
        self.original_data_dir = None
        
        # Mock database
        self.mock_db = MockDB()
        
        # Initialize pattern learner with test directory
        self.learner = SC2PatternLearner(self.mock_db, logger, data_dir=self.test_data_dir)
        
        # Test data
        self.test_game_data = {
            'opponent_name': 'TestPlayer',
            'opponent_race': 'Protoss',
            'result': 'Victory',
            'map': 'TestMap',
            'duration': '20m 30s',
            'date': '2025-08-29 18:00:00',
            'build_order': [
                {'name': 'Probe', 'supply': 10, 'time': 30},
                {'name': 'Probe', 'supply': 11, 'time': 60},
                {'name': 'Pylon', 'supply': 12, 'time': 90},
                {'name': 'Probe', 'supply': 13, 'time': 120},
                {'name': 'Probe', 'supply': 14, 'time': 150},
                {'name': 'Gateway', 'supply': 15, 'time': 180}
            ]
        }
        
        self.test_comment = "gateway expand to stalker pressure with blink upgrade"
        
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.test_data_dir):
            shutil.rmtree(self.test_data_dir)
    
    def test_improved_build_order_structure(self):
        """Test that build orders are stored with count and order information"""
        # Process comment to create pattern
        self.learner._process_new_comment(self.test_game_data, self.test_comment)
        
        # Load patterns and verify structure
        patterns_file = os.path.join(self.test_data_dir, 'patterns.json')
        self.assertTrue(os.path.exists(patterns_file))
        
        with open(patterns_file, 'r') as f:
            patterns = json.load(f)
        
        # Check that we have a pattern
        self.assertIn('pattern_001', patterns)
        pattern = patterns['pattern_001']
        
        # Verify improved build order structure
        self.assertIn('signature', pattern)
        signature = pattern['signature']
        
        # Check early game structure
        self.assertIn('early_game', signature)
        early_game = signature['early_game']
        
        # Should have consolidated units with counts
        probe_entries = [entry for entry in early_game if entry['unit'] == 'Probe']
        self.assertEqual(len(probe_entries), 2)  # Two probe groups (split by Pylon)
        self.assertEqual(probe_entries[0]['count'], 2)  # First 2 probes
        self.assertEqual(probe_entries[1]['count'], 2)  # Last 2 probes
        
        # Check order preservation
        self.assertEqual(early_game[0]['order'], 1)  # First probe group
        self.assertEqual(early_game[1]['order'], 2)  # Pylon
        self.assertEqual(early_game[2]['order'], 3)  # Second probe group
    
    def test_dual_comment_storage(self):
        """Test that both raw and cleaned comments are stored"""
        # Process comment
        self.learner._process_new_comment(self.test_game_data, self.test_comment)
        
        # Load comments and verify dual storage
        comments_file = os.path.join(self.test_data_dir, 'comments.json')
        self.assertTrue(os.path.exists(comments_file))
        
        with open(comments_file, 'r') as f:
            comments_data = json.load(f)
        
        # Check comment structure
        self.assertIn('comments', comments_data)
        comments = comments_data['comments']
        self.assertEqual(len(comments), 1)
        
        comment = comments[0]
        
        # Verify both raw and cleaned versions exist
        self.assertIn('raw_comment', comment)
        self.assertIn('cleaned_comment', comment)
        
        # Raw should be exactly as provided
        self.assertEqual(comment['raw_comment'], self.test_comment)
        
        # Cleaned should remove punctuation and normalize
        self.assertIn('gateway', comment['cleaned_comment'])
        self.assertIn('expand', comment['cleaned_comment'])
        self.assertIn('stalker', comment['cleaned_comment'])
        self.assertIn('pressure', comment['cleaned_comment'])
        self.assertIn('blink', comment['cleaned_comment'])
    
    def test_improved_keyword_extraction(self):
        """Test that keywords are properly extracted without punctuation or duplicates"""
        # Process comment
        self.learner._process_new_comment(self.test_game_data, self.test_comment)
        
        # Load patterns and check keywords
        patterns_file = os.path.join(self.test_data_dir, 'patterns.json')
        with open(patterns_file, 'r') as f:
            patterns = json.load(f)
        
        pattern = patterns['pattern_001']
        keywords = pattern['keywords']
        
        # Should have clean keywords without punctuation
        expected_keywords = ['gateway', 'expand', 'stalker', 'pressure', 'blink']
        self.assertEqual(set(keywords), set(expected_keywords))
        
        # No duplicates
        self.assertEqual(len(keywords), len(set(keywords)))
        
        # No punctuation artifacts
        for keyword in keywords:
            self.assertNotIn(',', keyword)
            self.assertNotIn('.', keyword)
            self.assertNotIn('!', keyword)
    
    def test_build_order_consolidation(self):
        """Test that consecutive identical units are consolidated with counts"""
        # First, process the initial comment to create pattern_001
        self.learner._process_new_comment(self.test_game_data, self.test_comment)
        
        # Create test data with many consecutive probes
        probe_heavy_game = self.test_game_data.copy()
        probe_heavy_game['build_order'] = [
            {'name': 'Probe', 'supply': 10, 'time': 30},
            {'name': 'Probe', 'supply': 11, 'time': 60},
            {'name': 'Probe', 'supply': 12, 'time': 90},
            {'name': 'Probe', 'supply': 13, 'time': 120},
            {'name': 'Pylon', 'supply': 14, 'time': 150},
            {'name': 'Probe', 'supply': 15, 'time': 180},
            {'name': 'Probe', 'supply': 16, 'time': 210}
        ]
        
        # Process second comment to create pattern_002
        self.learner._process_new_comment(probe_heavy_game, "probe heavy opening")
        
        # Load patterns and verify consolidation
        patterns_file = os.path.join(self.test_data_dir, 'patterns.json')
        with open(patterns_file, 'r') as f:
            patterns = json.load(f)
        
        # Should have pattern_002 now
        self.assertIn('pattern_002', patterns)
        pattern = patterns['pattern_002']
        
        signature = pattern['signature']
        early_game = signature['early_game']
        
        # First entry should be consolidated probes
        first_entry = early_game[0]
        self.assertEqual(first_entry['unit'], 'Probe')
        self.assertEqual(first_entry['count'], 4)  # First 4 probes
        self.assertEqual(first_entry['order'], 1)
        
        # Second entry should be Pylon
        second_entry = early_game[1]
        self.assertEqual(second_entry['unit'], 'Pylon')
        self.assertEqual(second_entry['count'], 1)
        self.assertEqual(second_entry['order'], 2)
        
        # Third entry should be remaining probes
        third_entry = early_game[2]
        self.assertEqual(third_entry['unit'], 'Probe')
        self.assertEqual(third_entry['count'], 2)  # Last 2 probes
        self.assertEqual(third_entry['order'], 3)
    
    def test_keyword_indexing(self):
        """Test that keywords are properly indexed for fast lookup"""
        # Process comment
        self.learner._process_new_comment(self.test_game_data, self.test_comment)
        
        # Load comments and check keyword index
        comments_file = os.path.join(self.test_data_dir, 'comments.json')
        with open(comments_file, 'r') as f:
            comments_data = json.load(f)
        
        # Check keyword index exists
        self.assertIn('keyword_index', comments_data)
        keyword_index = comments_data['keyword_index']
        
        # Each keyword should reference the comment
        for keyword in ['gateway', 'expand', 'stalker', 'pressure', 'blink']:
            self.assertIn(keyword, keyword_index)
            self.assertIn('comment_001', keyword_index[keyword])
    
    def test_data_consistency(self):
        """Test that all data files are consistent with each other"""
        # Process comment
        self.learner._process_new_comment(self.test_game_data, self.test_comment)
        
        # Load all data files
        patterns_file = os.path.join(self.test_data_dir, 'patterns.json')
        comments_file = os.path.join(self.test_data_dir, 'comments.json')
        stats_file = os.path.join(self.test_data_dir, 'learning_stats.json')
        
        with open(patterns_file, 'r') as f:
            patterns = json.load(f)
        with open(comments_file, 'r') as f:
            comments_data = json.load(f)
        with open(stats_file, 'r') as f:
            stats = json.load(f)
        
        # Check consistency
        pattern = patterns['pattern_001']
        comment = comments_data['comments'][0]
        
        # Pattern should reference comment
        self.assertEqual(pattern['comment_id'], comment['id'])
        
        # Keywords should match
        self.assertEqual(set(pattern['keywords']), set(comment['keywords']))
        
        # Stats should reflect the data
        self.assertEqual(stats['total_patterns'], 1)
        self.assertEqual(stats['total_keywords'], 5)

# Mock database for testing
class MockDB:
    def update_player_comments_in_last_replay(self, comment):
        return True
    
    def get_player_comments(self, player_name, player_race):
        return []

if __name__ == '__main__':
    unittest.main()
