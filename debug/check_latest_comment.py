"""Check if latest comment has build_order"""
import json

with open('data/comments.json', 'r') as f:
    d = json.load(f)

comments = d.get('comments', [])
print(f"Total comments: {len(comments)}")

# Show last 5 comments
print("\nLast 5 comments:")
for c in comments[-5:]:
    comment = c.get('comment', 'NO COMMENT')[:50]
    gd = c.get('game_data', {})
    bo_len = len(gd.get('build_order', []))
    opp = gd.get('opponent_name', 'Unknown')
    print(f"  '{comment}...' - opponent: {opp}, build_order: {bo_len} steps")



