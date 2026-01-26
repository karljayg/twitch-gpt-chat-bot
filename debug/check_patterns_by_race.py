"""Check pattern counts by race"""
import json

with open('data/patterns.json', 'r', encoding='utf-8') as f:
    patterns = json.load(f)

with open('data/comments.json', 'r', encoding='utf-8') as f:
    comments_data = json.load(f)

print("=== patterns.json ===")
race_counts = {}
for name, p in patterns.items():
    race = p.get('race', 'unknown').lower()
    race_counts[race] = race_counts.get(race, 0) + 1
for race, count in sorted(race_counts.items()):
    print(f"  {race}: {count}")

print("\n=== comments.json ===")
comments = comments_data.get('comments', [])
race_counts2 = {}
for c in comments:
    race = c.get('game_data', {}).get('opponent_race', 'unknown')
    if race:
        race = race.lower()
    else:
        race = 'unknown'
    race_counts2[race] = race_counts2.get(race, 0) + 1
for race, count in sorted(race_counts2.items()):
    print(f"  {race}: {count}")



