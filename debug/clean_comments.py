"""Remove the corrupted entries from comments.json too"""
import json

with open('data/comments.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

comments = data.get('comments', [])
print(f"Before: {len(comments)} comments")

# Comments to remove (same as patterns we deleted)
to_remove = [
    '14 pool lings, then muta',
    'roach ling all in counter',
    '12 pool',
    '12 pool to roach',
    '12 pool to upgraded roach push',
    'roach based play',
    '2 base roach timing attack',
    'Three base ling-bane aggression into roach',
    '3 hatch ling lair muta roach',
    '3-hatch Ling Bane in roach all in'
]

new_comments = []
removed = []

for c in comments:
    comment_text = c.get('comment', '').lower()
    should_remove = False
    for pattern in to_remove:
        if pattern.lower() in comment_text:
            should_remove = True
            removed.append(c.get('comment', '')[:50])
            break
    if not should_remove:
        new_comments.append(c)

print(f"Removed: {len(removed)}")
for r in removed:
    print(f"  - {r}")

data['comments'] = new_comments
print(f"After: {len(new_comments)} comments")

with open('data/comments.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
print("Saved!")



