from settings import config


class GameInfo:
    """
    GameInfo class for parsing SC2 game data from localhost JSON API
    
    IMPORTANT: BLIZZARD API BUG
    ===========================
    The SC2 localhost JSON API now always returns "isReplay: true" even for real games.
    This broke the previous logic that relied on the isReplay flag to distinguish
    between real games and replay viewing.
    
    WORKAROUND: We now detect real games by checking if the streamer is actually
    playing (present in the players list). This means:
    - Real games you play = MATCH_STARTED/MATCH_ENDED
    - Watching replays = Also detected as MATCH_STARTED/MATCH_ENDED (until Blizzard fixes it)
    
    TODO: Revert this workaround when Blizzard fixes their API
    """
    def __init__(self, json_data):
        # BLIZZARD API BUG: isReplay is always "true" even for real games
        # We can't rely on this field anymore - see get_status() method for workaround
        self.isReplay = json_data['isReplay']
        self.players = json_data['players']
        self.displayTime = json_data['displayTime']
        self.total_players = len(self.players)
        self.config = config

    def _is_streamer_account(self, player_name):
        """Case-insensitive check if player name is one of the streamer's accounts"""
        player_lower = player_name.lower()
        return any(alias.lower() == player_lower for alias in config.SC2_PLAYER_ACCOUNTS)

    def get_player_names(self, result_filter=None):
        return [config.STREAMER_NICKNAME if self._is_streamer_account(player['name']) else player['name'] for player
                in self.players if result_filter is None or player['result'] == result_filter]

    # TODO: fix the replay parser as support for Random is not provided
    # hence the DB has never saved race as Random period
    # then we will need to rerun all the replays to fix old data as well
    RACE_MAPPING = {
        'terr': 'Terran',
        'prot': 'Protoss',
        'random': 'Random', 
        'zerg': 'Zerg',
    }

    def get_player_race(self, player_name):
        lower_player_name = player_name.lower()
        for player in self.players:
            if player['name'].lower() == lower_player_name:
                race = player['race'].lower()
                return self.RACE_MAPPING.get(race, 'Unknown')
        return 'Unknown'  # Return a default value indicating the race is unknown

    # get opponent's race
    def get_opponent_race(self, player_name):
        lower_player_name = player_name.lower()
        for player in self.players:
            if player['name'].lower() != lower_player_name:
                race = player['race'].lower()
                return self.RACE_MAPPING.get(race, 'Unknown')
        return 'Unknown'  # Return a default value indicating the race is unknown

    def get_status(self):
        # BLIZZARD API BUG: isReplay is always "true" even for real games
        # This broke the SC2 localhost JSON API - we can't rely on isReplay flag anymore
        # TODO: Fix this when/if Blizzard fixes their API
        # 
        # WORKAROUND: We now detect real games by checking if the streamer is actually playing
        # This means watching replays will also be detected as "real games" until Blizzard fixes it
        streamer_playing = any(self._is_streamer_account(player['name']) for player in self.players)
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"GameInfo.get_status() - isReplay: {self.isReplay} (BLIZZARD BUG: always true), streamer_playing: {streamer_playing}")
        logger.debug(f"Players: {[p['name'] for p in self.players]}")
        logger.debug(f"Results: {[p['result'] for p in self.players]}")
        
        if all(player['result'] == 'Undecided' for player in self.players):
            # Game is starting
            if streamer_playing:
                logger.debug("Detected MATCH_STARTED (streamer is playing - ignoring broken isReplay flag)")
                return "MATCH_STARTED"  # Streamer is playing = real game (regardless of broken isReplay)
            else:
                # Can't trust isReplay flag anymore, assume it's a replay if streamer not playing
                logger.debug("Detected REPLAY_STARTED (streamer not playing - assuming replay due to Blizzard API bug)")
                return "REPLAY_STARTED"
        elif any(player['result'] in ['Defeat', 'Victory', 'Tie'] for player in self.players):
            # Game has ended
            if streamer_playing:
                logger.debug("Detected MATCH_ENDED (streamer was playing - ignoring broken isReplay flag)")
                return "MATCH_ENDED"  # Streamer was playing = real game ended (regardless of broken isReplay)
            else:
                # Can't trust isReplay flag anymore, assume it's a replay if streamer not playing
                logger.debug("Detected REPLAY_ENDED (streamer not playing - assuming replay due to Blizzard API bug)")
                return "REPLAY_ENDED"
        return None

    def get_winner(self):
        for player in self.players:
            if player['result'] == 'Victory':
                return player['name']
        return None
