import requests
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from settings.config import TOKEN  # Import TOKEN after fixing the path

# Override CLIENT_ID directly here
CLIENT_ID = "q6batx0epp608isickayubi39itsckt"  # Replace with the new Client ID
CHANNEL_NAME = "kj_freeedom"  # Replace with the target Twitch channel

def validate_token():
    """Validate the token and confirm it matches the client ID."""
    headers = {'Authorization': f'Bearer {TOKEN}'}
    response = requests.get('https://id.twitch.tv/oauth2/validate', headers=headers)
    if response.status_code != 200:
        raise Exception("Invalid TOKEN. Check your config.py values.")
    data = response.json()
    if data['client_id'] != CLIENT_ID:
        raise Exception(f"TOKEN does not match CLIENT_ID. TOKEN's Client ID: {data['client_id']}")
    print("Token validation successful.")

def get_channel_id(channel_name):
    """Fetch the channel ID for the given channel name."""
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'Client-Id': CLIENT_ID
    }
    params = {'login': channel_name}

    response = requests.get('https://api.twitch.tv/helix/users', headers=headers, params=params)
    print(f"Response Status Code: {response.status_code}")
    if response.status_code != 200:
        print("Error Details:", response.json())  # Print error details
    response.raise_for_status()
    return response.json()['data'][0]['id']

def get_clips(channel_id):
    """Fetch clips for the given channel ID."""
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'Client-Id': CLIENT_ID
    }
    params = {
        'broadcaster_id': channel_id,
        'first': 100
    }
    clips = []
    while True:
        response = requests.get('https://api.twitch.tv/helix/clips', headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        clips.extend(data['data'])
        pagination = data.get('pagination', {}).get('cursor')
        if not pagination:
            break
        params['after'] = pagination
    return clips

def download_clips(clips, download_dir='clips'):
    """Download clips to the specified directory."""
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    for clip in clips:
        url = clip['thumbnail_url'].split('-preview')[0] + '.mp4'
        title = clip['title'].replace(' ', '_').replace('/', '_')
        output_path = os.path.join(download_dir, f"{title}.mp4")
        response = requests.get(url)
        with open(output_path, 'wb') as file:
            file.write(response.content)
        print(f"Downloaded: {title}")

def main():
    validate_token()  # Ensure TOKEN and CLIENT_ID are valid
    channel_id = get_channel_id(CHANNEL_NAME)
    print(f"Channel ID: {channel_id}")
    clips = get_clips(channel_id)
    print(f"Found {len(clips)} clips.")
    download_clips(clips)

if __name__ == "__main__":
    main()
