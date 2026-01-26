"""
API Database Client

REST API client for remote database operations.
Communicates with the PHP API server.
"""

import requests
import logging
from typing import List, Dict, Any, Optional
from core.interfaces import IDatabaseClient

# Suppress SSL warnings when verification is disabled
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ApiDatabaseClient(IDatabaseClient):
    """
    REST API client for remote database operations.
    Used when DB_MODE='api' in config.
    """
    
    def __init__(self, api_base_url: str = None, api_key: str = None, verify_ssl: bool = None):
        # Lazy import to avoid circular dependencies and allow mocking in tests
        from settings import config
        
        self.api_base_url = api_base_url if api_base_url is not None else config.DB_API_URL
        self.api_key = api_key if api_key is not None else config.DB_API_KEY
        self.verify_ssl = verify_ssl if verify_ssl is not None else getattr(config, 'DB_API_VERIFY_SSL', True)
        
        self._logger = logging.getLogger("ApiDatabaseClient")
        self._request_count = 0  # Initialize counter BEFORE making any requests
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
        
        if not self.verify_ssl:
            self._logger.warning("SSL verification disabled - use only for testing!")
        
        self._logger.info(f"ApiDatabaseClient initialized for {self.api_base_url}")
    
    def _make_request(self, method: str, endpoint: str, data: dict = None) -> Any:
        """Generic API request handler with error handling"""
        url = f"{self.api_base_url}{endpoint}"
        
        self._request_count += 1
        
        # Log every 10th request to avoid spam, but always log first 3
        if self._request_count <= 3 or self._request_count % 10 == 0:
            self._logger.debug(f"API Request #{self._request_count}: {method} {endpoint}")
        
        try:
            if method == 'GET':
                response = self.session.get(url, params=data, timeout=10, verify=self.verify_ssl)
            elif method == 'POST':
                response = self.session.post(url, json=data, timeout=10, verify=self.verify_ssl)
            elif method == 'PUT':
                response = self.session.put(url, json=data, timeout=10, verify=self.verify_ssl)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            # Check for HTTP errors and log details before raising
            if response.status_code >= 400:
                try:
                    error_body = response.json()
                    error_msg = error_body.get('message', error_body.get('error', 'Unknown error'))
                    self._logger.error(f"API HTTP {response.status_code} error: {method} {endpoint}")
                    self._logger.error(f"  Error message: {error_msg}")
                    if 'details' in error_body:
                        self._logger.error(f"  Details: {error_body['details']}")
                except (ValueError, KeyError):
                    # If response isn't JSON, log the raw text
                    self._logger.error(f"API HTTP {response.status_code} error: {method} {endpoint}")
                    self._logger.error(f"  Response: {response.text[:200]}")
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.HTTPError as e:
            # This is raised by raise_for_status() - already logged above
            self._logger.error(f"HTTP error raised: {method} {endpoint} - {e}")
            raise
        except requests.exceptions.SSLError as e:
            self._logger.error(f"SSL Certificate error: {e}")
            self._logger.error(f"If this is a valid self-signed cert, you may need to add it to your system's trust store")
            raise
        except requests.exceptions.RequestException as e:
            self._logger.error(f"API request failed: {method} {endpoint} - {e}")
            raise
    
    # ===== Player Operations =====
    
    def check_player_and_race_exists(self, player_name: str, player_race: str) -> Optional[Dict]:
        return self._make_request('GET', '/api/v1/players/check', {
            'player_name': player_name,
            'player_race': player_race
        })
    
    def check_player_exists(self, player_name: str) -> Optional[Dict]:
        return self._make_request('GET', f'/api/v1/players/{player_name}/exists')
    
    def get_player_records(self, player_name: str) -> List[str]:
        result = self._make_request('GET', f'/api/v1/players/{player_name}/records')
        return result if isinstance(result, list) else []
    
    def get_player_comments(self, player_name: str, player_race: str) -> List[Dict]:
        result = self._make_request('GET', f'/api/v1/players/{player_name}/comments', {
            'race': player_race
        })
        return result if isinstance(result, list) else []
    
    def get_player_overall_records(self, player_name: str) -> str:
        result = self._make_request('GET', f'/api/v1/players/{player_name}/overall_records')
        if isinstance(result, dict) and 'records' in result:
            return result['records']
        return str(result)
    
    def get_player_race_matchup_records(self, player_name: str) -> str:
        """Get race matchup records for a player"""
        result = self._make_request('GET', f'/api/v1/players/{player_name}/race_matchup_records')
        if isinstance(result, dict) and 'records' in result:
            return result['records']
        return str(result)
    
    def get_head_to_head_matchup(self, player1: str, player2: str) -> List[str]:
        """Get head-to-head matchup records between two players"""
        result = self._make_request('GET', '/api/v1/players/head_to_head', {
            'player1': player1,
            'player2': player2
        })
        return result if isinstance(result, list) else []
    
    # ===== Replay Operations =====
    
    def get_last_replay_info(self) -> Optional[Dict]:
        return self._make_request('GET', '/api/v1/replays/last')
    
    def get_latest_replay(self) -> Optional[Dict]:
        """Get latest replay with processed data (opponent, map, result, etc.)"""
        result = self._make_request('GET', '/api/v1/replays/latest')
        if not result:
            return None
        
        # Process result to determine opponent (matches Python logic)
        from settings import config
        streamer_accounts = [name.lower() for name in config.SC2_PLAYER_ACCOUNTS]
        
        player1_name = result.get('Player1_Name', '')
        player2_name = result.get('Player2_Name', '')
        
        if player1_name.lower() in streamer_accounts:
            opponent = player2_name
            result_str = result.get('Player1_Result', '')
        else:
            opponent = player1_name
            result_str = result.get('Player2_Result', '')
        
        return {
            'opponent': opponent,
            'map': result.get('map', ''),
            'result': result_str,
            'date': result.get('date', ''),
            'duration': result.get('duration', ''),
            'timestamp': result.get('timestamp', 0),
            'existing_comment': result.get('existing_comment')
        }
    
    def get_replay_by_id(self, replay_id: int) -> Optional[Dict]:
        return self._make_request('GET', f'/api/v1/replays/{replay_id}')
    
    def get_games_for_last_x_hours(self, hours: int) -> List[str]:
        """Get games played in the last X hours"""
        result = self._make_request('GET', '/api/v1/replays/games', {'hours': hours})
        return result if isinstance(result, list) else []
    
    def extract_opponent_build_order(self, opponent_name: str, opp_race: str, 
                                     streamer_picked_race: str) -> Optional[List[str]]:
        result = self._make_request('GET', '/api/v1/build_orders/extract', {
            'opponent_name': opponent_name,
            'opponent_race': opp_race,
            'streamer_race': streamer_picked_race
        })
        return result if isinstance(result, list) else None
    
    def insert_replay_info(self, replay_summary: str) -> bool:
        """Insert replay information into database"""
        result = self._make_request('POST', '/api/v1/replays', {
            'replay_summary': replay_summary
        })
        return result.get('success', False) if isinstance(result, dict) else False
    
    def update_player_comments_in_last_replay(self, comment: str) -> bool:
        """Update player comment for the last replay"""
        result = self._make_request('PUT', '/api/v1/replays/last/comment', {
            'comment': comment
        })
        return result.get('success', False) if isinstance(result, dict) else False
    
    def save_player_comment_with_data(self, comment_data: Dict) -> bool:
        """Save full comment data to PlayerComments table with keywords, build_order, etc."""
        result = self._make_request('POST', '/api/v1/comments/save', {
            'comment_data': comment_data
        })
        return result.get('success', False) if isinstance(result, dict) else False
    
    def save_pattern_to_db(self, pattern_entry: Dict) -> bool:
        """Save pattern to PatternLearning table"""
        result = self._make_request('POST', '/api/v1/patterns/save', {
            'pattern_entry': pattern_entry
        })
        return result.get('success', False) if isinstance(result, dict) else False
    
    # ===== Connection Management =====
    
    def ensure_connection(self):
        """API doesn't need explicit connection management"""
        return True
    
    def keep_connection_alive(self):
        """API doesn't need heartbeat"""
        pass
    
    # ===== Legacy Compatibility =====
    
    @property
    def cursor(self):
        """Not applicable for API client - for legacy compatibility only"""
        raise NotImplementedError("API client doesn't use cursors. Update your code to use the interface methods.")
    
    @property
    def connection(self):
        """Not applicable for API client - for legacy compatibility only"""
        raise NotImplementedError("API client doesn't use direct connections. Update your code to use the interface methods.")
    
    @property
    def logger(self):
        return self._logger

