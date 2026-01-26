"""Check cannon rush pattern timing"""
import json

with open('data/patterns.json', 'r', encoding='utf-8') as f:
    patterns = json.load(f)

# Find cannon rush patterns
for name, p in patterns.items():
    comment = p.get('comment', '').lower()
    if 'cannon' in comment:
        print(f"\n{name}: '{p.get('comment', '')[:50]}'")
        sig = p.get('signature', {})
        eg = sig.get('early_game', [])
        
        # Find Forge timing
        for step in eg:
            unit = step.get('unit', '').lower()
            if 'forge' in unit:
                print(f"  Forge timing: {step.get('time', 'N/A')}s")
                break
        else:
            print(f"  No Forge found in early_game")
        
        # Show first 5 items
        items = [f"{s.get('unit', '')}@{s.get('time', 0)}" for s in eg[:8]]
        print(f"  First items: {items}")



