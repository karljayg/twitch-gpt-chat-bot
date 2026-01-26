"""Check data files only - no imports"""
import json

print("=" * 60)
print("DATA VERIFICATION")
print("=" * 60)

# Check patterns.json race labels
print("\n[TEST] Patterns.json Race Labels")
print("-" * 40)

with open('data/patterns.json', 'r') as f:
    patterns = json.load(f)

protoss_keywords = ['adept', 'stalker', 'zealot', 'carrier', 'void ray', 'oracle', 'gateway', 'prism', 'immortal', 'archon']
wrong_labels = []

for key in patterns.keys():
    if key.startswith('pattern_'):
        p = patterns[key]
        comment = p.get('comment', '').lower()
        race = p.get('race', 'unknown')
        
        if any(kw in comment for kw in protoss_keywords) and race != 'protoss':
            wrong_labels.append(f"{key}: '{comment[:40]}...' tagged as '{race}'")

print(f"Total patterns: {len([k for k in patterns.keys() if k.startswith('pattern_')])}")
print(f"Protoss patterns with wrong race labels: {len(wrong_labels)}")

if len(wrong_labels) == 0:
    print("✓ Race labels correct in patterns.json")
else:
    print(f"⚠️  {len(wrong_labels)} patterns have wrong race!")
    for w in wrong_labels[:5]:
        print(f"   {w}")

# Check comments.json
print("\n[TEST] Comments.json")
print("-" * 40)

with open('data/comments.json', 'r') as f:
    comments = json.load(f)

total_comments = len(comments.get('comments', []))
with_build_order = sum(1 for c in comments.get('comments', []) 
                       if c.get('game_data', {}).get('build_order'))

print(f"Total comments: {total_comments}")
print(f"With build order data: {with_build_order}")

print("\n" + "=" * 60)
print("DATA VERIFICATION COMPLETE")
print("=" * 60)



