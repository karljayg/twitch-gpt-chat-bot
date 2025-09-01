from settings import config


class GameInfo:
    """
    GameInfo class for parsing SC2 game data from localhost JSON API
    
    The SC2 localhost JSON API now correctly returns "isReplay: false" for real games
    and "isReplay: true" for replay viewing. The previous workarounds are no longer needed.
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
        # The isReplay flag now works correctly - we can trust it again
        # Real games: isReplay = false, Watching replays: isReplay = true
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"GameInfo.get_status() - isReplay: {self.isReplay}")
        logger.debug(f"Players: {[p['name'] for p in self.players]}")
        logger.debug(f"Results: {[p['result'] for p in self.players]}")
        
        if all(player['result'] == 'Undecided' for player in self.players):
            # Game is starting
            if self.isReplay:
                logger.debug("Detected REPLAY_STARTED (isReplay = true)")
                return "REPLAY_STARTED"
            else:
                logger.debug("Detected MATCH_STARTED (isReplay = false)")
                return "MATCH_STARTED"
        elif any(player['result'] in ['Defeat', 'Victory', 'Tie'] for player in self.players):
            # Game has ended
            if self.isReplay:
                logger.debug("Detected REPLAY_ENDED (isReplay = true)")
                return "REPLAY_ENDED"
            else:
                logger.debug("Detected MATCH_ENDED (isReplay = false)")
                return "MATCH_ENDED"
        return None

    def get_winner(self):
        for player in self.players:
            if player['result'] == 'Victory':
                return player['name']
        return None
