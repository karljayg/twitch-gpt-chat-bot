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
        from datetime import datetime
        
        self.api_base_url = api_base_url if api_base_url is not None else config.DB_API_URL
        self.api_key = api_key if api_key is not None else config.DB_API_KEY
        self.verify_ssl = verify_ssl if verify_ssl is not None else getattr(config, 'DB_API_VERIFY_SSL', True)
        
        # Setup logger with file handler (similar to Database class)
        self._logger = logging.getLogger("api_logger")
        self._logger.setLevel(logging.DEBUG)
        
        # Create timestamped log file for API operations
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
        log_file_name = f"logs/api_{timestamp}.log"
        
        # Only add file handler if not already present (avoid duplicates in tests)
        if not any(isinstance(h, logging.FileHandler) for h in self._logger.handlers):
            file_handler = logging.FileHandler(log_file_name, encoding='utf-8')
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)
        
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
        self._logger.info(f"API logging to: {log_file_name}")
    
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
        result = self._make_request('GET', '/api/v1/players/check', {
            'player_name': player_name,
            'player_race': player_race
        })
        if result:
            self._logger.debug(f"Player and race exists: {player_name} ({player_race}) - {result}")
        else:
            self._logger.debug(f"Player and race not found: {player_name} ({player_race})")
        return result
    
    def check_player_exists(self, player_name: str) -> Optional[Dict]:
        result = self._make_request('GET', f'/api/v1/players/{player_name}/exists')
        if result:
            self._logger.debug(f"Player exists: {result}")
        else:
            self._logger.debug(f"Player not found: {player_name}")
        return result
    
    def get_player_records(self, player_name: str) -> List[str]:
        result = self._make_request('GET', f'/api/v1/players/{player_name}/records')
        return result if isinstance(result, list) else []
    
    def get_player_comments(self, player_name: str, player_race: str) -> List[Dict]:
        result = self._make_request('GET', f'/api/v1/players/{player_name}/comments', {
            'race': player_race
        })
        comments = result if isinstance(result, list) else []
        self._logger.debug(f"Retrieved {len(comments)} comments for {player_name} ({player_race})")
        return comments
    
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
            'replay_id': result.get('ReplayId', result.get('replay_id')),
            'opponent': opponent,
            'map': result.get('map', result.get('Map', '')),
            'result': result_str,
            'date': result.get('date', ''),
            'duration': result.get('duration', ''),
            'timestamp': result.get('timestamp', 0),
            'existing_comment': result.get('existing_comment')
        }

    def get_replay_by_recency_offset(self, offset: int) -> Optional[Dict]:
        off = max(0, int(offset))
        try:
            result = self._make_request('GET', f'/api/v1/replays/recency/{off}')
        except Exception:
            return None
        if not isinstance(result, dict) or result.get('error'):
            return None
        rid = result.get('ReplayId') or result.get('replay_id')
        if rid is None:
            return None
        return self.get_replay_by_id(int(rid))
    
    def get_replay_by_id(self, replay_id: int) -> Optional[Dict]:
        result = self._make_request('GET', f'/api/v1/replays/{replay_id}')
        if not isinstance(result, dict):
            return result

        # Normalize API row shape to legacy keys expected by services.
        if "opponent" in result:
            return result

        # API may return raw DB columns (Replay_Summary, Date_Played, Player1_Name, etc.)
        from settings import config
        p1_name = str(result.get("Player1_Name", ""))
        p2_name = str(result.get("Player2_Name", ""))
        p1_race = result.get("Player1_Race", "Unknown")
        p2_race = result.get("Player2_Race", "Unknown")
        p1_result = result.get("Player1_Result", "Unknown")
        p2_result = result.get("Player2_Result", "Unknown")
        streamer_accounts = [n.lower() for n in getattr(config, "SC2_PLAYER_ACCOUNTS", [])]

        if p1_name.lower() in streamer_accounts:
            opponent = p2_name or "Unknown"
            opponent_race = p2_race
            streamer_race = p1_race
            result_str = p1_result
        elif p2_name.lower() in streamer_accounts:
            opponent = p1_name or "Unknown"
            opponent_race = p1_race
            streamer_race = p2_race
            result_str = p2_result
        else:
            # Observer / unknown: best effort fallback.
            opponent = p2_name or p1_name or "Unknown"
            opponent_race = p2_race if p2_name else p1_race
            streamer_race = "Unknown"
            result_str = "Observed"

        return {
            "replay_id": result.get("ReplayId", replay_id),
            "opponent": opponent,
            "opponent_race": opponent_race,
            "streamer_race": streamer_race,
            "player1_name": p1_name,
            "player2_name": p2_name,
            "player1_race": p1_race,
            "player2_race": p2_race,
            "map": result.get("Map", result.get("map", "")),
            "result": result_str,
            "date": str(result.get("Date_Played", result.get("date", ""))),
            "duration": result.get("GameDuration", result.get("duration", "")),
            "timestamp": result.get("UnixTimestamp", result.get("timestamp", 0)),
            "existing_comment": result.get("Player_Comments", result.get("existing_comment")),
            "replay_summary": result.get("Replay_Summary", result.get("replay_summary", "")),
        }
    
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
        # Extract key info from replay summary for logging
        lines = replay_summary.split('\n')
        players_line = next((l for l in lines if l.startswith('Players:')), 'Players: unknown')
        map_line = next((l for l in lines if l.startswith('Map:')), 'Map: unknown')
        
        self._logger.debug(f"Inserting replay: {players_line}, {map_line}")
        
        result = self._make_request('POST', '/api/v1/replays', {
            'replay_summary': replay_summary
        })
        success = result.get('success', False) if isinstance(result, dict) else False
        
        if success:
            self._logger.info(f"✓ Saved replay summary")
        else:
            self._logger.error(f"✗ Failed to save replay summary")
        
        return success
    
    def update_player_comments_in_last_replay(self, comment: str) -> bool:
        """Update player comment for the last replay"""
        result = self._make_request('PUT', '/api/v1/replays/last/comment', {
            'comment': comment
        })
        return result.get('success', False) if isinstance(result, dict) else False

    def update_player_comments_by_replay_id(self, replay_id: int, comment: str) -> bool:
        """Update player comment for a specific ReplayId."""
        result = self._make_request('PUT', f'/api/v1/replays/{replay_id}/comment', {
            'comment': comment
        })
        return result.get('success', False) if isinstance(result, dict) else False
    
    def save_player_comment_with_data(self, comment_data: Dict) -> bool:
        """Save full comment data to PlayerComments table with keywords, build_order, etc."""
        opponent = comment_data.get('opponent_name', 'unknown')
        comment = comment_data.get('comment', '')[:50] + ('...' if len(comment_data.get('comment', '')) > 50 else '')
        self._logger.debug(f"Saving comment for {opponent}: '{comment}'")
        
        result = self._make_request('POST', '/api/v1/comments/save', {
            'comment_data': comment_data
        })
        success = result.get('success', False) if isinstance(result, dict) else False
        
        if success:
            self._logger.info(f"✓ Saved comment for {opponent}")
        else:
            self._logger.error(f"✗ Failed to save comment for {opponent}")
        
        return success
    
    def save_pattern_to_db(self, pattern_entry: Dict) -> bool:
        """Save pattern to PatternLearning table"""
        keywords = pattern_entry.get('keywords', [])
        opponent = pattern_entry.get('opponent_name', 'unknown')
        self._logger.debug(f"Saving pattern for {opponent} with {len(keywords)} keywords")
        
        result = self._make_request('POST', '/api/v1/patterns/save', {
            'pattern_entry': pattern_entry
        })
        success = result.get('success', False) if isinstance(result, dict) else False
        
        if success:
            self._logger.info(f"✓ Saved pattern for {opponent}")
        else:
            self._logger.error(f"✗ Failed to save pattern for {opponent}")
        
        return success
    
    # ===== FSL (psistorm via api-server GET /api/v1/fsl/*; read-only) =====
    
    def fsl_players_search(self, q: str, limit: int = 40) -> Dict[str, Any]:
        result = self._make_request(
            'GET', '/api/v1/fsl/players/search', {'q': q, 'limit': limit}
        )
        return result if isinstance(result, dict) else {}
    
    def fsl_player_by_id(self, player_id: int) -> Optional[Dict[str, Any]]:
        result = self._make_request(
            'GET', f'/api/v1/fsl/players/{int(player_id)}', None
        )
        if isinstance(result, dict) and result.get('player'):
            return result['player']
        return None
    
    def fsl_player_by_name_exact(self, name: str) -> Optional[Dict[str, Any]]:
        result = self._make_request(
            'GET', '/api/v1/fsl/players/by-name', {'name': name}
        )
        if isinstance(result, dict) and result.get('player'):
            return result['player']
        return None
    
    def fsl_teams_search(self, q: str, limit: int = 40) -> Dict[str, Any]:
        result = self._make_request(
            'GET', '/api/v1/fsl/teams/search', {'q': q, 'limit': limit}
        )
        return result if isinstance(result, dict) else {}
    
    def fsl_team_by_id(self, team_id: int) -> Optional[Dict[str, Any]]:
        result = self._make_request(
            'GET', f'/api/v1/fsl/teams/{int(team_id)}', None
        )
        if isinstance(result, dict) and result.get('team'):
            return result['team']
        return None

    def fsl_team_players(self, team_id: int) -> Dict[str, Any]:
        try:
            result = self._make_request(
                'GET',
                f'/api/v1/fsl/teams/{int(team_id)}/players',
                None,
            )
            return result if isinstance(result, dict) else {}
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                self._logger.warning(
                    "FSL GET /api/v1/fsl/teams/{id}/players not on server (404) — "
                    "deploy api-server FslDatabase::listPlayersForTeam + fsl.php route"
                )
                return {
                    'players': [],
                    'count': 0,
                    '_roster_endpoint_unavailable': True,
                }
            raise

    def fsl_leaderboard_maps_won(self, limit: int = 15) -> Dict[str, Any]:
        params: Dict[str, Any] = {'limit': max(1, int(limit))}
        try:
            result = self._make_request(
                'GET',
                '/api/v1/fsl/statistics/leaderboard/maps-won',
                params,
            )
            return result if isinstance(result, dict) else {}
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                self._logger.warning(
                    "FSL GET .../leaderboard/maps-won not on server (404) — deploy api-server"
                )
                return {
                    'leaderboard': [],
                    'count': 0,
                    '_maps_won_endpoint_unavailable': True,
                }
            raise

    def fsl_schedule(
        self,
        season: Optional[int] = None,
        week: Optional[int] = None,
        limit: int = 120,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {'limit': limit}
        if season is not None:
            params['season'] = season
        if week is not None:
            params['week'] = week
        result = self._make_request('GET', '/api/v1/fsl/schedule', params)
        return result if isinstance(result, dict) else {}
    
    def fsl_schedule_entry(self, schedule_id: int) -> Optional[Dict[str, Any]]:
        result = self._make_request(
            'GET', f'/api/v1/fsl/schedule/{int(schedule_id)}', None
        )
        if isinstance(result, dict) and result.get('entry'):
            return result['entry']
        return None
    
    def fsl_schedule_match_links(self, schedule_id: int) -> Dict[str, Any]:
        result = self._make_request(
            'GET', f'/api/v1/fsl/schedule/{int(schedule_id)}/matches', None
        )
        return result if isinstance(result, dict) else {}

    def fsl_team_league_season_summary(self, season: int) -> Dict[str, Any]:
        try:
            result = self._make_request(
                'GET',
                f'/api/v1/fsl/team-league/season/{int(season)}/summary',
                None,
            )
            return result if isinstance(result, dict) else {}
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                self._logger.warning(
                    "FSL GET .../team-league/season/{n}/summary not on server (404)"
                )
                return {'summary': {}, '_team_league_summary_unavailable': True}
            raise

    def fsl_solo_division_season_standings(
        self, season: int, division: str
    ) -> Dict[str, Any]:
        """division: single letter S, A, or B (fsl_matches.t_code)."""
        d = str(division).strip().upper()
        if len(d) != 1 or d not in ("S", "A", "B"):
            return {"summary": {}, "_solo_division_standings_unavailable": True}
        try:
            result = self._make_request(
                "GET",
                f"/api/v1/fsl/solo-league/season/{int(season)}/division/{d}/standings",
                None,
            )
            return result if isinstance(result, dict) else {}
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code in (404, 400):
                self._logger.warning(
                    "FSL GET .../solo-league/season/{n}/division/{S|A|B}/standings not on server or bad request"
                )
                return {"summary": {}, "_solo_division_standings_unavailable": True}
            raise

    def fsl_matches(
        self,
        season: Optional[int] = None,
        player_name: Optional[str] = None,
        player_id: Optional[int] = None,
        opponent_name: Optional[str] = None,
        limit: int = 60,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {'limit': limit}
        if season is not None:
            params['season'] = season
        if player_name:
            params['player_name'] = player_name
        if player_id is not None:
            params['player_id'] = player_id
        if opponent_name:
            params['opponent_name'] = opponent_name
        result = self._make_request('GET', '/api/v1/fsl/matches', params)
        return result if isinstance(result, dict) else {}

    def fsl_matches_h2h(
        self,
        player_name: str,
        opponent_name: str,
        season: Optional[int] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            'player_name': player_name,
            'opponent_name': opponent_name,
        }
        if season is not None:
            params['season'] = int(season)
        try:
            result = self._make_request(
                'GET', '/api/v1/fsl/matches/h2h', params
            )
            return result if isinstance(result, dict) else {}
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                self._logger.warning(
                    "FSL GET /api/v1/fsl/matches/h2h not on server (404) — deploy api-server"
                )
                return {'h2h': {}, '_h2h_endpoint_unavailable': True}
            raise

    def fsl_match_by_id(self, fsl_match_id: int) -> Optional[Dict[str, Any]]:
        result = self._make_request(
            'GET', f'/api/v1/fsl/matches/{int(fsl_match_id)}', None
        )
        if isinstance(result, dict) and result.get('match'):
            return result['match']
        return None
    
    def fsl_statistics_for_player(self, player_id: int) -> Dict[str, Any]:
        result = self._make_request(
            'GET', f'/api/v1/fsl/statistics/player/{int(player_id)}', None
        )
        return result if isinstance(result, dict) else {}

    def fsl_leaderboard_match_win_pct(
        self, min_matches: int = 10, limit: int = 15
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            'min_matches': max(1, int(min_matches)),
            'limit': max(1, int(limit)),
        }
        result = self._make_request(
            'GET',
            '/api/v1/fsl/statistics/leaderboard/win-pct',
            params,
        )
        return result if isinstance(result, dict) else {}

    def fsl_leaderboard_match_total_wins(
        self, min_matches: int = 1, limit: int = 15
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            'min_matches': max(1, int(min_matches)),
            'limit': max(1, int(limit)),
        }
        try:
            result = self._make_request(
                'GET',
                '/api/v1/fsl/statistics/leaderboard/total-wins',
                params,
            )
            return result if isinstance(result, dict) else {}
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                self._logger.warning(
                    "FSL GET .../leaderboard/total-wins not on server (404) — deploy api-server"
                )
                return {
                    'leaderboard': [],
                    'count': 0,
                    '_total_wins_endpoint_unavailable': True,
                }
            raise

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

