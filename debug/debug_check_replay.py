"""Check which replay is being processed vs which was commented"""
import os
import glob
from settings import config
from datetime import datetime

# Get the latest replay file
replays = glob.glob(os.path.join(config.REPLAYS_FOLDER, "*.SC2Replay"))
if replays:
    latest = max(replays, key=os.path.getmtime)
    mtime = os.path.getmtime(latest)
    mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
    print(f"Latest replay file: {os.path.basename(latest)}")
    print(f"  Modified: {mtime_str}")
else:
    print("No replay files found")

# Check the comment's date
import json
with open('data/comments.json', 'r') as f:
    d = json.load(f)

for c in d['comments']:
    if '1 base reaper bunker' in c.get('comment', '').lower():
        print(f"\nStored comment date: {c.get('game_data', {}).get('date')}")
        print(f"Comment: {c.get('comment')}")
        break

print("\n=== Compare ===")
print("If the replay file timestamp doesn't match the comment date,")
print("then 'please retry' is processing a DIFFERENT game!")



