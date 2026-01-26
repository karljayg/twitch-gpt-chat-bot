import json

with open('data/patterns.json', 'r') as f:
    d = json.load(f)

print(f"patterns.json keys: {list(d.keys())}")
print(f"'patterns' list length: {len(d.get('patterns', []))}")

# Check if there are pattern_X keys
pattern_keys = [k for k in d.keys() if k.startswith('pattern_')]
print(f"pattern_X keys: {len(pattern_keys)}")

# List all patterns/comments
if d.get('patterns'):
    print("\nAll patterns in 'patterns' list:")
    for i, p in enumerate(d['patterns'][:10]):
        print(f"  {i}: {p.get('comment', 'NO COMMENT')}")
        
if pattern_keys:
    print(f"\nFirst 10 pattern_X entries:")
    for k in pattern_keys[:10]:
        p = d[k]
        print(f"  {k}: {p.get('comment', 'NO COMMENT')}, race={p.get('race')}")



