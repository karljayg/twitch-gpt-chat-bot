"""Check spawningtool time format"""
import spawningtool.parser
import glob
import os
from settings import config

# Find the latest replay
replays = glob.glob(os.path.join(config.REPLAYS_FOLDER, "*.SC2Replay"))
if not replays:
    print("No replays found")
    exit(1)

latest = max(replays, key=os.path.getmtime)
print(f"Parsing: {latest}")

replay_data = spawningtool.parser.parse_replay(latest)

# Find opponent player
for p_key, p_data in replay_data['players'].items():
    name = p_data.get('name', '')
    print(f"\nPlayer: {name}")
    build_order = p_data.get('buildOrder', [])
    print(f"Build order steps: {len(build_order)}")
    
    if build_order:
        print("First 10 steps:")
        for step in build_order[:10]:
            print(f"  {step}")
        
        print(f"\nTime type: {type(build_order[0].get('time'))}")
        print(f"Name type: {type(build_order[0].get('name'))}")
        print(f"Supply type: {type(build_order[0].get('supply'))}")



