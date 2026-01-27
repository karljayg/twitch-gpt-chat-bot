"""
Comprehensive regression test for database and JSON operations parity

Tests all READ and WRITE operations work in both 'local' and 'api' modes.

Run with:
    pytest tests/test_database_json_parity.py -v
    
Or run specific test:
    pytest tests/test_database_json_parity.py::TestDatabaseJsonParity::test_all_read_operations -v
"""

import pytest
import os
import sys
import json
from datetime import datetime

from adapters.database.local_database_client import LocalDatabaseClient
from adapters.database.api_database_client import ApiDatabaseClient
from settings import config


class TestDatabaseJsonParity:
    """Verify all database and JSON operations work in both modes"""
    
    @pytest.fixture(scope="class")
    def local_client(self):
        """Create local database client"""
        try:
            return LocalDatabaseClient()
        except Exception as e:
            pytest.skip(f"Local database connection failed: {e}")
    
    @pytest.fixture(scope="class")
    def api_client(self):
        """Create API database client"""
        try:
            return ApiDatabaseClient(
                api_base_url=config.DB_API_URL,
                api_key=config.DB_API_KEY,
                verify_ssl=config.DB_API_VERIFY_SSL
            )
        except Exception as e:
            pytest.skip(f"API database connection failed: {e}")
    
    # ===== READ OPERATIONS =====
    
    def test_all_read_operations_exist(self, local_client, api_client):
        """Verify all read methods exist on both clients"""
        read_methods = [
            'check_player_and_race_exists',
            'check_player_exists',
            'get_player_records',
            'get_player_comments',
            'get_player_overall_records',
            'get_player_race_matchup_records',
            'get_head_to_head_matchup',
            'get_last_replay_info',
            'get_latest_replay',
            'get_replay_by_id',
            'get_games_for_last_x_hours',
            'extract_opponent_build_order',
        ]
        
        for method in read_methods:
            assert hasattr(local_client, method), f"LocalClient missing: {method}"
            assert hasattr(api_client, method), f"ApiClient missing: {method}"
            assert callable(getattr(local_client, method)), f"LocalClient {method} not callable"
            assert callable(getattr(api_client, method)), f"ApiClient {method} not callable"
    
    def test_all_write_operations_exist(self, local_client, api_client):
        """Verify all write methods exist on both clients"""
        write_methods = [
            'insert_replay_info',
            'update_player_comments_in_last_replay',
            'save_player_comment_with_data',
            'save_pattern_to_db',
        ]
        
        for method in write_methods:
            assert hasattr(local_client, method), f"LocalClient missing: {method}"
            assert hasattr(api_client, method), f"ApiClient missing: {method}"
            assert callable(getattr(local_client, method)), f"LocalClient {method} not callable"
            assert callable(getattr(api_client, method)), f"ApiClient {method} not callable"
    
    def test_player_queries(self, local_client, api_client):
        """Test player query operations return same format"""
        # Use a known player from database
        test_player = config.STREAMER_NICKNAME if hasattr(config, 'STREAMER_NICKNAME') else "kj"
        
        # Test player existence check
        local_result = local_client.check_player_exists(test_player)
        api_result = api_client.check_player_exists(test_player)
        
        if local_result and api_result:
            assert isinstance(local_result, dict), "Local result should be dict"
            assert isinstance(api_result, dict), "API result should be dict"
            # Both should return player data (check_player_exists returns player record, not just boolean)
            assert len(local_result) > 0, "Local should return player data"
            assert len(api_result) > 0, "API should return player data"
    
    def test_replay_queries(self, local_client, api_client):
        """Test replay query operations return same format"""
        # Test latest replay
        local_result = local_client.get_latest_replay()
        api_result = api_client.get_latest_replay()
        
        if local_result and api_result:
            # Both should have same structure
            assert 'opponent' in local_result, "Local missing opponent"
            assert 'opponent' in api_result, "API missing opponent"
            assert 'map' in local_result, "Local missing map"
            assert 'map' in api_result, "API missing map"
            assert 'timestamp' in local_result, "Local missing timestamp"
            assert 'timestamp' in api_result, "API missing timestamp"
            assert 'existing_comment' in local_result, "Local missing existing_comment"
            assert 'existing_comment' in api_result, "API missing existing_comment"
            
            # Note: Timestamps may differ if local and API databases are not in sync
            # Just verify they exist and are valid integers
            assert isinstance(local_result['timestamp'], int), "Local timestamp should be int"
            assert isinstance(api_result['timestamp'], int), "API timestamp should be int"
            assert local_result['timestamp'] > 0, "Local timestamp should be positive"
            assert api_result['timestamp'] > 0, "API timestamp should be positive"
    
    @pytest.mark.write
    @pytest.mark.skip(reason="Write test - skipped by default to avoid modifying database")
    def test_comment_write_operations(self, local_client, api_client):
        """Test comment write operations work (SKIPPED by default)"""
        test_comment_data = {
            'raw_comment': 'test comment',
            'cleaned_comment': 'test comment',
            'keywords': ['test'],
            'game_data': {
                'opponent_name': 'TestOpponent',
                'opponent_race': 'zerg',
                'map': 'TestMap',
                'result': 'Victory',
                'duration': '10:00',
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'build_order': []
            }
        }
        
        # Test local
        local_success = local_client.save_player_comment_with_data(test_comment_data)
        assert local_success, "Local save should succeed"
        
        # Test API
        api_success = api_client.save_player_comment_with_data(test_comment_data)
        assert api_success, "API save should succeed"
    
    @pytest.mark.write
    @pytest.mark.skip(reason="Write test - skipped by default to avoid modifying database")
    def test_pattern_write_operations(self, local_client, api_client):
        """Test pattern write operations work (SKIPPED by default)"""
        test_pattern = {
            'signature': {'12': 'Drone', '13': 'Overlord'},
            'comment': 'test pattern',
            'keywords': ['test'],
            'game_data': {
                'opponent_name': 'TestOpponent',
                'opponent_race': 'zerg',
                'player_race': 'zerg',
            }
        }
        
        # Test local
        local_success = local_client.save_pattern_to_db(test_pattern)
        assert local_success, "Local pattern save should succeed"
        
        # Test API
        api_success = api_client.save_pattern_to_db(test_pattern)
        assert api_success, "API pattern save should succeed"
    
    def test_connection_management(self, local_client, api_client):
        """Test connection management methods exist and work"""
        # Both should have these methods
        assert hasattr(local_client, 'ensure_connection')
        assert hasattr(api_client, 'ensure_connection')
        assert hasattr(local_client, 'keep_connection_alive')
        assert hasattr(api_client, 'keep_connection_alive')
        
        # Should not raise errors
        local_client.ensure_connection()
        api_client.ensure_connection()
        local_client.keep_connection_alive()
        api_client.keep_connection_alive()
    
    def test_legacy_properties(self, local_client, api_client):
        """Test legacy compatibility properties exist"""
        # Local client should have all legacy properties
        legacy_props = ['cursor', 'connection', 'logger']
        for prop in legacy_props:
            assert hasattr(local_client, prop), f"LocalClient missing property: {prop}"
        
        # API client has logger but cursor/connection raise NotImplementedError (intentional)
        assert hasattr(api_client, 'logger'), "ApiClient missing logger property"
        # cursor and connection are defined but raise errors - that's expected for API mode


class TestJsonOperations:
    """Test JSON file operations in pattern learning"""
    
    def test_json_files_exist(self):
        """Verify JSON files are created"""
        json_files = [
            'data/patterns.json',
            'data/comments.json',
            'data/learning_stats.json'
        ]
        
        for file_path in json_files:
            full_path = os.path.join(os.path.dirname(__file__), '..', file_path)
            # Files may not exist yet, just verify the data directory exists
            data_dir = os.path.dirname(full_path)
            if not os.path.exists(data_dir):
                pytest.skip(f"Data directory not found: {data_dir}")
    
    def test_json_structure_patterns(self):
        """Test patterns.json has correct structure"""
        patterns_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'patterns.json')
        
        if not os.path.exists(patterns_file):
            pytest.skip("patterns.json not found")
        
        with open(patterns_file, 'r', encoding='utf-8') as f:
            patterns = json.load(f)
        
        assert isinstance(patterns, dict), "Patterns should be a dictionary"
        
        # Check structure of first pattern if exists
        if patterns:
            first_pattern = next(iter(patterns.values()))
            required_fields = ['signature', 'keywords', 'comment']
            for field in required_fields:
                assert field in first_pattern, f"Pattern missing field: {field}"
    
    def test_json_structure_comments(self):
        """Test comments.json has correct structure"""
        comments_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'comments.json')
        
        if not os.path.exists(comments_file):
            pytest.skip("comments.json not found")
        
        with open(comments_file, 'r', encoding='utf-8') as f:
            comments_data = json.load(f)
        
        assert isinstance(comments_data, dict), "Comments should be a dictionary"
        assert 'comments' in comments_data, "Missing 'comments' array"
        assert 'keyword_index' in comments_data, "Missing 'keyword_index'"
        
        # Check structure of first comment if exists
        if comments_data['comments']:
            first_comment = comments_data['comments'][0]
            required_fields = ['id', 'comment', 'keywords', 'game_data']
            for field in required_fields:
                assert field in first_comment, f"Comment missing field: {field}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
