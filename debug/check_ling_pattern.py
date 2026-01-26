"""Check what's in the 3 hatch ling pattern signature"""
import json

with open('data/patterns.json', 'r', encoding='utf-8') as f:
    patterns = json.load(f)

# Find the 3 hatch ling pattern
for name, p in patterns.items():
    comment = p.get('comment', '')
    if '3 hatch ling all in' in comment.lower():
        print(f"\n{name}: {comment}")
        sig = p.get('signature', {})
        print(f"\nSignature early_game ({len(sig.get('early_game', []))} items):")
        for item in sig.get('early_game', [])[:15]:
            print(f"  {item}")
        print(f"\nSignature key_timings:")
        for k, v in sig.get('key_timings', {}).items():
            print(f"  {k}: {v}")
        break



