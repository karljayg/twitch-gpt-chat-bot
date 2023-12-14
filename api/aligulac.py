import requests
from settings import config

ALIGULAC_API_KEY = config.ALIGULAC_API_KEY
YOUR_API_KEY = ALIGULAC_API_KEY
BASE_URL = 'http://aligulac.com'  # Replace with the correct base URL


def search_player_by_tag(tag):
    url = f'{BASE_URL}/api/v1/player/?tag={tag}&limit=10&apikey={YOUR_API_KEY}&format=json&limit=10'
    response = requests.get(url)

    if response.status_code == 200:
        players = response.json()
        if players and 'objects' in players:
            return players['objects']
        else:
            return None
    else:
        print("Error in the request", response.status_code)
        return None


def get_player_matches(player_id):
    url = f'{BASE_URL}/api/v1/results/?id={player_id}&limit=10&apikey={YOUR_API_KEY}&format=json&limit=10'
    response = requests.get(url)

    if response.status_code == 200:
        return response.json().get('objects', [])
    else:
        print("Error in the request", response.status_code)
        return None


def player_overview(player_id):
    response = requests.get(f'{BASE_URL}/api/v1/player/{player_id}/overview')
    return response.json() if response.status_code == 200 else None


def player_details(player_id):
    response = requests.get(f'{BASE_URL}/api/v1/player/{player_id}')
    return response.json() if response.status_code == 200 else None


def player_season_statistics(player_id):
    response = requests.get(f'{BASE_URL}/api/v1/player/{player_id}/season')
    return response.json() if response.status_code == 200 else None


def ladder_information(season_id, region_id):
    response = requests.get(
        f'{BASE_URL}/api/v1/ladder/{season_id}/{region_id}')
    return response.json() if response.status_code == 200 else None


def search_players(query):
    response = requests.get(f'{BASE_URL}/api/v1/search/{query}')
    return response.json() if response.status_code == 200 else None


def seasons_list():
    response = requests.get(f'{BASE_URL}/api/v1/season')
    return response.json() if response.status_code == 200 else None


player_tag = 'Dark'  # Replace with the in-game tag of the player you're searching for
players = search_player_by_tag(player_tag)

if players:
    for player in players:
        print("Player found:", player['tag'])
        print("Full Name:", player['name'])
        print("ID:", player['id'])
        print("Country:", player['country'])
        print("Race:", player['race'])

        player_matches = get_player_matches(player['id'])
        if player_matches:
            for match in player_matches:
                print("Match:", match)
else:
    print("No player found with that tag")

# Call to get an overview of a player with a given player ID
player_id = 1  # Replace with an appropriate player ID
overview = player_overview(player_id)
print("Player Overview:", overview)

# Call to get details of a player with a given player ID
details = player_details(player_id)
print("Player Details:", details)

# Call to get season statistics of a player with a given player ID
season_stats = player_season_statistics(player_id)
print("Player Season Statistics:", season_stats)

# Call to get ladder information for a given season and region
season_id = 1  # Replace with an appropriate season ID
region_id = 1  # Replace with an appropriate region ID
ladder_info = ladder_information(season_id, region_id)
print("Ladder Information:", ladder_info)

# Call to search for players based on a query string
query = 'Dark'  # Replace with a query string
search_results = search_players(query)
print("Search Results:", search_results)

# Call to get a list of all seasons
seasons = seasons_list()
print("Seasons List:", seasons)
