import json

with open('data/patterns.json', 'r') as f:
    d = json.load(f)

print("=== Protoss-related patterns ===")
for p in d.get('patterns', []):
    comment = p.get('comment', '').lower()
    if 'adept' in comment or 'carrier' in comment or 'zealot' in comment or 'stalker' in comment:
        print(f"Comment: {p.get('comment')}")
        print(f"  race field: {p.get('race')}")
        sig = p.get('signature', {})
        early_game = sig.get('early_game', [])[:5]
        print(f"  early_game (first 5): {[s.get('unit') for s in early_game]}")
        print()



