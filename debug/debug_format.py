"""Debug the build order format differences"""
import json
import sys
sys.path.insert(0, '.')

# Load comments.json to see what format is stored
with open('data/comments.json', 'r') as f:
    comments = json.load(f)

# Find the target comment
for c in comments['comments']:
    if '1 base reaper bunker' in c.get('comment', '').lower():
        stored_bo = c['game_data'].get('build_order', [])
        print("=== STORED BUILD ORDER FORMAT (comments.json) ===")
        print(f"Total steps: {len(stored_bo)}")
        print("First 5 steps:")
        for step in stored_bo[:5]:
            print(f"  {step}")
        print("\nStep keys:", list(stored_bo[0].keys()) if stored_bo else "N/A")
        break

# Now let's look at the replay data format by reading a recent log or the replay analyzer output
# Actually, let's trace through and see how the replay_data is structured

print("\n\n=== Expected format from replay_data ===")
print("The replay analyzer returns buildOrder with these keys:")
print("  - 'name': unit/building name")
print("  - 'time': integer seconds")  
print("  - 'supply': integer supply count")
print("\nIf these match, format is correct.")
print("\nLet's also check if there are duplicate steps that might cause issues...")

# Check for consecutive duplicates
print("\n=== Checking for pattern issues in stored build ===")
seen_strategic = []
for step in stored_bo:
    name = step.get('name', '')
    if name.lower() in ['reaper', 'factory', 'bunker', 'hellion', 'armory', 'starport']:
        seen_strategic.append({'name': name, 'time': step.get('time', 0)})

print(f"Strategic items in stored build: {len(seen_strategic)}")
for item in seen_strategic:
    print(f"  {item['name']} @ {item['time']}s")



