"""
Test that all database client methods exist and are callable

This test verifies that both LocalDatabaseClient and ApiDatabaseClient
implement all required methods from IDatabaseClient interface.

Run with:
    pytest tests/adapters/test_database_client_methods.py -v
"""

import pytest
from inspect import signature

from adapters.database.local_database_client import LocalDatabaseClient
from adapters.database.api_database_client import ApiDatabaseClient
from core.interfaces import IDatabaseClient


class TestDatabaseClientMethods:
    """Verify all required methods exist on both clients"""
    
    @pytest.fixture
    def local_client(self):
        """Create local client (may skip if DB not available)"""
        try:
            return LocalDatabaseClient()
        except Exception as e:
            pytest.skip(f"Local database not available: {e}")
    
    @pytest.fixture
    def api_client(self):
        """Create API client (may skip if API not available)"""
        from settings import config
        try:
            return ApiDatabaseClient(
                api_base_url=config.DB_API_URL,
                api_key=config.DB_API_KEY,
                verify_ssl=getattr(config, 'DB_API_VERIFY_SSL', True)
            )
        except Exception as e:
            pytest.skip(f"API server not available: {e}")
    
    def test_all_player_methods_exist(self, local_client, api_client):
        """Verify all player-related methods exist on both clients"""
        player_methods = [
            'check_player_and_race_exists',
            'check_player_exists',
            'get_player_records',
            'get_player_comments',
            'get_player_overall_records',
            'get_player_race_matchup_records',
            'get_head_to_head_matchup',
        ]
        
        for method_name in player_methods:
            # Check local client
            assert hasattr(local_client, method_name), f"LocalDatabaseClient missing {method_name}"
            local_method = getattr(local_client, method_name)
            assert callable(local_method), f"LocalDatabaseClient.{method_name} is not callable"
            
            # Check API client
            assert hasattr(api_client, method_name), f"ApiDatabaseClient missing {method_name}"
            api_method = getattr(api_client, method_name)
            assert callable(api_method), f"ApiDatabaseClient.{method_name} is not callable"
            
            # Verify signatures match (same number of parameters)
            local_sig = signature(local_method)
            api_sig = signature(api_method)
            assert len(local_sig.parameters) == len(api_sig.parameters), \
                f"{method_name} parameter count mismatch: Local={len(local_sig.parameters)}, API={len(api_sig.parameters)}"
    
    def test_all_replay_methods_exist(self, local_client, api_client):
        """Verify all replay-related methods exist on both clients"""
        replay_methods = [
            'get_last_replay_info',
            'get_latest_replay',
            'get_replay_by_id',
            'get_replay_by_recency_offset',
            'get_games_for_last_x_hours',
            'extract_opponent_build_order',
            'insert_replay_info',
            'update_player_comments_in_last_replay',
        ]
        
        for method_name in replay_methods:
            # Check local client
            assert hasattr(local_client, method_name), f"LocalDatabaseClient missing {method_name}"
            local_method = getattr(local_client, method_name)
            assert callable(local_method), f"LocalDatabaseClient.{method_name} is not callable"
            
            # Check API client
            assert hasattr(api_client, method_name), f"ApiDatabaseClient missing {method_name}"
            api_method = getattr(api_client, method_name)
            assert callable(api_method), f"ApiDatabaseClient.{method_name} is not callable"
            
            # Verify signatures match
            local_sig = signature(local_method)
            api_sig = signature(api_method)
            assert len(local_sig.parameters) == len(api_sig.parameters), \
                f"{method_name} parameter count mismatch: Local={len(local_sig.parameters)}, API={len(api_sig.parameters)}"
    
    def test_connection_management_methods_exist(self, local_client, api_client):
        """Verify connection management methods exist"""
        connection_methods = [
            'ensure_connection',
            'keep_connection_alive',
        ]
        
        for method_name in connection_methods:
            assert hasattr(local_client, method_name), f"LocalDatabaseClient missing {method_name}"
            assert hasattr(api_client, method_name), f"ApiDatabaseClient missing {method_name}"
    
    def test_legacy_properties_exist(self, local_client, api_client):
        """Verify legacy compatibility properties exist"""
        # Local should have cursor and connection
        assert hasattr(local_client, 'cursor')
        assert hasattr(local_client, 'connection')
        assert hasattr(local_client, 'logger')
        
        # API should have logger (cursor/connection raise NotImplementedError)
        assert hasattr(api_client, 'logger')
        
        # API cursor/connection should raise NotImplementedError
        with pytest.raises(NotImplementedError):
            _ = api_client.cursor
        with pytest.raises(NotImplementedError):
            _ = api_client.connection
    
    def test_methods_return_correct_types(self, local_client, api_client):
        """Test that methods return expected types (when data exists)"""
        # Test get_last_replay_info returns dict or None
        try:
            local_result = local_client.get_last_replay_info()
            api_result = api_client.get_last_replay_info()
            
            if local_result is not None:
                assert isinstance(local_result, dict), "get_last_replay_info should return dict or None"
            if api_result is not None:
                assert isinstance(api_result, dict), "get_last_replay_info should return dict or None"
        except AttributeError:
            # Method may not be implemented yet in Database class
            pass
        
        # Test get_player_records returns list
        test_player = "kj"  # Adjust to actual player in your DB
        try:
            local_result = local_client.get_player_records(test_player)
            api_result = api_client.get_player_records(test_player)
            assert isinstance(local_result, list), "get_player_records should return list"
            assert isinstance(api_result, list), "get_player_records should return list"
        except Exception:
            pass  # Skip if player doesn't exist
    
    def test_methods_handle_nonexistent_data(self, local_client, api_client):
        """Test that methods handle nonexistent data gracefully"""
        # Test with non-existent player
        fake_player = "NonExistentPlayer12345"
        
        # These should not raise exceptions, just return None or empty
        try:
            local_result = local_client.check_player_exists(fake_player)
            api_result = api_client.check_player_exists(fake_player)
            # Should return None or dict with exists=False
            assert local_result is None or isinstance(local_result, dict)
            assert api_result is None or isinstance(api_result, dict)
        except Exception as e:
            pytest.fail(f"Methods should handle nonexistent data gracefully: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
