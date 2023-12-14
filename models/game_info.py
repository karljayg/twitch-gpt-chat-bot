from settings import config


class GameInfo:
    def __init__(self, json_data):
        self.isReplay = json_data['isReplay']
        self.players = json_data['players']
        self.displayTime = json_data['displayTime']
        self.total_players = len(self.players)
        self.config = config

    def get_player_names(self, result_filter=None):
        return [config.STREAMER_NICKNAME if player['name'] in config.SC2_PLAYER_ACCOUNTS else player['name'] for player
                in self.players if result_filter is None or player['result'] == result_filter]

    RACE_MAPPING = {
        'terr': 'Terran',
        'prot': 'Protoss',
        'random': 'Rand',
        'zerg': 'Zerg',
    }

    def get_player_race(self, player_name):
        lower_player_name = player_name.lower()
        for player in self.players:
            if player['name'].lower() == lower_player_name:
                race = player['race'].lower()
                return self.RACE_MAPPING.get(race, 'Unknown')
        return 'Unknown'  # Return a default value indicating the race is unknown

    def get_status(self):
        if all(player['result'] == 'Undecided' for player in self.players):
            return "REPLAY_STARTED" if self.isReplay else "MATCH_STARTED"
        elif any(player['result'] in ['Defeat', 'Victory', 'Tie'] for player in self.players):
            return "REPLAY_ENDED" if self.isReplay else "MATCH_ENDED"
        return None

    def get_winner(self):
        for player in self.players:
            if player['result'] == 'Victory':
                return player['name']
        return None
