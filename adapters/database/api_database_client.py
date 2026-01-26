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
            
            response.raise_for_status()
            return response.json()
        
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
    
    # ===== Replay Operations =====
    
    def get_last_replay_info(self) -> Optional[Dict]:
        return self._make_request('GET', '/api/v1/replays/last')
    
    def get_replay_by_id(self, replay_id: int) -> Optional[Dict]:
        return self._make_request('GET', f'/api/v1/replays/{replay_id}')
    
    def extract_opponent_build_order(self, opponent_name: str, opp_race: str, 
                                     streamer_picked_race: str) -> Optional[List[str]]:
        result = self._make_request('GET', '/api/v1/build_orders/extract', {
            'opponent_name': opponent_name,
            'opponent_race': opp_race,
            'streamer_race': streamer_picked_race
        })
        return result if isinstance(result, list) else None
    
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

