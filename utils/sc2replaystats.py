import requests
import json
from settings import config

AUTH_KEY = config.SC2REPLAY_STATS_AUTH_KEY
ACCOUNT_ID = config.SC2REPLAY_STATS_ACCOUNT_ID
hash_value = config.SC2REPLAY_STATS_HASH
token_value = config.SC2REPLAY_STATS_TOKEN
timestamp_value = config.SC2REPLAY_STATS_TIMESTAMP

authorization_value = f"{hash_value};{token_value};{timestamp_value}"

headers = {
    "Authorization": authorization_value,
}

# Endpoint to get the last replay for the account
url = "http://api.sc2replaystats.com/account/last-replay"
response = requests.get(url, headers=headers)

# Check if the request was successful
if response.status_code == 200:
    pretty_json = json.dumps(response.json(), indent=4)
    print(pretty_json)
else:
    print(f"Error fetching last replay: {response.json()}")
