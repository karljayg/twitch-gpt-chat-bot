"""Check pattern structure in comments.json"""
import json

with open('data/comments.json', encoding='utf-8') as f:
    d = json.load(f)

print("Checking pattern structure:")
for i, pattern in enumerate(d.get('comments', [])[:5]):
    has_sig = 'signature' in pattern
    comment = pattern.get('comment', '')[:40]
    race = pattern.get('race', 'NO RACE FIELD')
    print(f"  {i}: sig={has_sig}, race='{race}', comment='{comment}'")

# Check specifically for baneling patterns
print("\nFirst baneling pattern structure:")
for pattern in d.get('comments', []):
    if 'bane' in pattern.get('comment', '').lower():
        has_sig = 'signature' in pattern
        race = pattern.get('race', 'NO RACE FIELD')
        sig_keys = list(pattern.get('signature', {}).keys()) if has_sig else []
        early_game_len = len(pattern.get('signature', {}).get('early_game', []))
        print(f"  sig={has_sig}, sig_keys={sig_keys}")
        print(f"  race='{race}'")
        print(f"  early_game={early_game_len} steps")
        print(f"  comment='{pattern.get('comment', '')}'")
        break

