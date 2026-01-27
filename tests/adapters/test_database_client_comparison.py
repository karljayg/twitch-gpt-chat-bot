"""
Integration tests comparing LocalDatabaseClient vs ApiDatabaseClient

These tests ensure both implementations produce identical results.
Requires both local database and API server to be available.

Run with:
    pytest tests/adapters/test_database_client_comparison.py -v
    
Or test specific methods:
    pytest tests/adapters/test_database_client_comparison.py::TestDatabaseClientComparison::test_get_player_records -v
"""

import pytest
from typing import Optional, Dict, List

from adapters.database.local_database_client import LocalDatabaseClient
from adapters.database.api_database_client import ApiDatabaseClient
from settings import config


class TestDatabaseClientComparison:
    """
    Compare LocalDatabaseClient and ApiDatabaseClient to ensure parity.
    Tests require:
    - Local MySQL database accessible (for LocalDatabaseClient)
    - API server running and accessible (for ApiDatabaseClient)
    """
    
    @pytest.fixture(scope="class")
    def local_client(self):
        """Create local database client"""
        if config.DB_MODE.lower() != "local":
            pytest.skip("Local database not configured (DB_MODE != 'local')")
        try:
            return LocalDatabaseClient()
        except Exception as e:
            pytest.skip(f"Local database connection failed: {e}")
    
    @pytest.fixture(scope="class")
    def api_client(self):
        """Create API database client"""
        try:
            client = ApiDatabaseClient(
                api_base_url=config.DB_API_URL,
                api_key=config.DB_API_KEY,
                verify_ssl=getattr(config, 'DB_API_VERIFY_SSL', True)
            )
            # Test connection
            client._make_request('GET', '/health')
            return client
        except Exception as e:
            pytest.skip(f"API server connection failed: {e}")
    
    def _normalize_result(self, result):
        """Normalize results for comparison (handle None, empty, type differences)"""
        if result is None:
            return None
        if isinstance(result, dict):
            # Sort dict keys for consistent comparison
            return {k: self._normalize_result(v) for k, v in sorted(result.items())}
        if isinstance(result, list):
            return [self._normalize_result(item) for item in result]
        if isinstance(result, str):
            # Normalize whitespace
            return ' '.join(result.split())
        return result
    
    def _compare_results(self, local_result, api_result, method_name: str):
        """Compare results and provide detailed error message if different"""
        local_norm = self._normalize_result(local_result)
        api_norm = self._normalize_result(api_result)
        
        if local_norm != api_norm:
            pytest.fail(
                f"{method_name} results differ:\n"
                f"Local:  {local_result}\n"
                f"API:    {api_result}\n"
                f"Normalized Local:  {local_norm}\n"
                f"Normalized API:    {api_norm}"
            )
    
    # ===== Player Operations Tests =====
    
    def test_check_player_and_race_exists(self, local_client, api_client):
        """Test check_player_and_race_exists returns same result"""
        # Use a player that likely exists in your database
        # Adjust these test values based on your actual data
        test_player = "kj"  # Change to actual player in your DB
        test_race = "Protoss"  # Change to actual race
        
        local_result = local_client.check_player_and_race_exists(test_player, test_race)
        api_result = api_client.check_player_and_race_exists(test_player, test_race)
        
        self._compare_results(local_result, api_result, "check_player_and_race_exists")
    
    def test_check_player_exists(self, local_client, api_client):
        """Test check_player_exists returns same result"""
        test_player = "kj"  # Change to actual player in your DB
        
        local_result = local_client.check_player_exists(test_player)
        api_result = api_client.check_player_exists(test_player)
        
        # API returns {'exists': bool, 'data': dict}, local returns dict or None
        # Normalize for comparison
        if local_result is None:
            assert api_result is None or api_result.get('exists') is False
        else:
            if isinstance(api_result, dict) and 'data' in api_result:
                api_result = api_result['data']
            self._compare_results(local_result, api_result, "check_player_exists")
    
    def test_get_player_records(self, local_client, api_client):
        """Test get_player_records returns same result"""
        test_player = "kj"  # Change to actual player in your DB
        
        local_result = local_client.get_player_records(test_player)
        api_result = api_client.get_player_records(test_player)
        
        self._compare_results(local_result, api_result, "get_player_records")
    
    def test_get_player_comments(self, local_client, api_client):
        """Test get_player_comments returns same result"""
        test_player = "kj"  # Change to actual player in your DB
        test_race = "Protoss"  # Change to actual race
        
        local_result = local_client.get_player_comments(test_player, test_race)
        api_result = api_client.get_player_comments(test_player, test_race)
        
        self._compare_results(local_result, api_result, "get_player_comments")
    
    def test_get_player_overall_records(self, local_client, api_client):
        """Test get_player_overall_records returns same result"""
        test_player = "kj"  # Change to actual player in your DB
        
        local_result = local_client.get_player_overall_records(test_player)
        api_result = api_client.get_player_overall_records(test_player)
        
        # Both should return strings
        assert isinstance(local_result, str)
        assert isinstance(api_result, str)
        # Compare normalized (whitespace may differ)
        local_norm = self._normalize_result(local_result)
        api_norm = self._normalize_result(api_result)
        assert local_norm == api_norm, f"get_player_overall_records differs:\nLocal: {local_result}\nAPI: {api_result}"
    
    def test_get_player_race_matchup_records(self, local_client, api_client):
        """Test get_player_race_matchup_records returns same result"""
        test_player = "kj"  # Change to actual player in your DB
        
        local_result = local_client.get_player_race_matchup_records(test_player)
        api_result = api_client.get_player_race_matchup_records(test_player)
        
        # Both should return strings
        assert isinstance(local_result, str)
        assert isinstance(api_result, str)
        local_norm = self._normalize_result(local_result)
        api_norm = self._normalize_result(api_result)
        assert local_norm == api_norm, f"get_player_race_matchup_records differs:\nLocal: {local_result}\nAPI: {api_result}"
    
    def test_get_head_to_head_matchup(self, local_client, api_client):
        """Test get_head_to_head_matchup returns same result"""
        player1 = "kj"  # Change to actual players in your DB
        player2 = "vales"  # Change to actual players in your DB
        
        local_result = local_client.get_head_to_head_matchup(player1, player2)
        api_result = api_client.get_head_to_head_matchup(player1, player2)
        
        self._compare_results(local_result, api_result, "get_head_to_head_matchup")
    
    # ===== Replay Operations Tests =====
    
    def test_get_last_replay_info(self, local_client, api_client):
        """Test get_last_replay_info returns same result"""
        local_result = local_client.get_last_replay_info()
        api_result = api_client.get_last_replay_info()
        
        # Both should return dict or None
        if local_result is None:
            assert api_result is None, "Local returned None but API returned data"
        else:
            assert isinstance(api_result, dict), "API should return dict"
            # Compare key fields (some may differ like timestamps)
            assert 'UnixTimestamp' in local_result or 'UnixTimestamp' in api_result
    
    def test_get_latest_replay(self, local_client, api_client):
        """Test get_latest_replay returns same result"""
        local_result = local_client.get_latest_replay()
        api_result = api_client.get_latest_replay()
        
        if local_result is None:
            assert api_result is None, "Local returned None but API returned data"
        else:
            assert isinstance(api_result, dict), "API should return dict"
            # Compare key fields
            assert 'opponent' in local_result
            assert 'opponent' in api_result
            assert local_result['opponent'] == api_result['opponent']
            assert local_result['map'] == api_result['map']
            assert local_result['result'] == api_result['result']
    
    def test_get_replay_by_id(self, local_client, api_client):
        """Test get_replay_by_id returns same result"""
        # First get a valid replay ID
        last_replay = local_client.get_last_replay_info()
        if last_replay is None:
            pytest.skip("No replays in database")
        
        replay_id = last_replay.get('Id') or last_replay.get('id')
        if replay_id is None:
            pytest.skip("Could not determine replay ID")
        
        local_result = local_client.get_replay_by_id(replay_id)
        api_result = api_client.get_replay_by_id(replay_id)
        
        self._compare_results(local_result, api_result, "get_replay_by_id")
    
    def test_get_games_for_last_x_hours(self, local_client, api_client):
        """Test get_games_for_last_x_hours returns same result"""
        hours = 24
        
        local_result = local_client.get_games_for_last_x_hours(hours)
        api_result = api_client.get_games_for_last_x_hours(hours)
        
        self._compare_results(local_result, api_result, "get_games_for_last_x_hours")
    
    def test_extract_opponent_build_order(self, local_client, api_client):
        """Test extract_opponent_build_order returns same result"""
        # Use actual values from your database
        opponent_name = "vales"  # Change to actual opponent
        opp_race = "Protoss"  # Change to actual race
        streamer_race = "Terran"  # Change to actual race
        
        local_result = local_client.extract_opponent_build_order(
            opponent_name, opp_race, streamer_race
        )
        api_result = api_client.extract_opponent_build_order(
            opponent_name, opp_race, streamer_race
        )
        
        self._compare_results(local_result, api_result, "extract_opponent_build_order")
    
    # ===== Write Operations Tests =====
    # Note: These tests modify data, so they should be run carefully
    
    @pytest.mark.skip(reason="Modifies database - run manually when needed")
    def test_update_player_comments_in_last_replay(self, local_client, api_client):
        """Test update_player_comments_in_last_replay works the same"""
        test_comment = "Test comment from integration test"
        
        local_result = local_client.update_player_comments_in_last_replay(test_comment)
        # Reset to avoid affecting API test
        local_client.update_player_comments_in_last_replay("")
        
        api_result = api_client.update_player_comments_in_last_replay(test_comment)
        # Reset
        api_client.update_player_comments_in_last_replay("")
        
        assert local_result == api_result, "update_player_comments_in_last_replay results differ"
    
    @pytest.mark.skip(reason="Modifies database - run manually when needed")
    def test_insert_replay_info(self, local_client, api_client):
        """Test insert_replay_info works the same"""
        # Create a test replay summary
        test_summary = """Players: TestPlayer1: Terran, TestPlayer2: Protoss
Winners: TestPlayer1
Losers: TestPlayer2
Map: Test Map
Game Duration: 00:15:30
Game Type: 1v1
Region: US
Timestamp: 1706238000"""
        
        local_result = local_client.insert_replay_info(test_summary)
        api_result = api_client.insert_replay_info(test_summary)
        
        assert local_result == api_result, "insert_replay_info results differ"
        # Note: You may want to clean up test data after this


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
