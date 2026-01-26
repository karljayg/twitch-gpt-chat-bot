"""Delete the 2 problematic patterns from patterns.json, comments.json, and database"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# First, get info about what we're deleting
print("=" * 60)
print("DELETING PROBLEMATIC PATTERNS")
print("=" * 60)

# Load patterns
with open('data/patterns.json', 'r', encoding='utf-8') as f:
    patterns = json.load(f)

# Get the comment IDs for these patterns
patterns_to_delete = ['pattern_227', 'pattern_452']
comment_ids_to_delete = []
comments_text_to_delete = []

for pattern_name in patterns_to_delete:
    p = patterns.get(pattern_name, {})
    if p:
        comment_id = p.get('comment_id', '')
        comment_text = p.get('comment', '')[:50]
        print(f"\n{pattern_name}:")
        print(f"  comment_id: {comment_id}")
        print(f"  comment: {comment_text}...")
        if comment_id:
            comment_ids_to_delete.append(comment_id)
            comments_text_to_delete.append(comment_text)

# Remove from patterns.json
print("\n[1] Removing from patterns.json...")
for pattern_name in patterns_to_delete:
    if pattern_name in patterns:
        del patterns[pattern_name]
        print(f"  Deleted: {pattern_name}")

with open('data/patterns.json', 'w', encoding='utf-8') as f:
    json.dump(patterns, f, indent=2)
print(f"  Saved patterns.json ({len(patterns)} patterns remaining)")

# Remove from comments.json
print("\n[2] Removing from comments.json...")
with open('data/comments.json', 'r', encoding='utf-8') as f:
    comments_data = json.load(f)

original_count = len(comments_data.get('comments', []))
comments_data['comments'] = [
    c for c in comments_data.get('comments', [])
    if c.get('id') not in comment_ids_to_delete
]
removed_count = original_count - len(comments_data['comments'])

with open('data/comments.json', 'w', encoding='utf-8') as f:
    json.dump(comments_data, f, indent=2)
print(f"  Removed {removed_count} comments")
print(f"  Saved comments.json ({len(comments_data['comments'])} comments remaining)")

# Remove from database
print("\n[3] Removing from database...")
try:
    from adapters.database.database_client_factory import create_database_client
    db = create_database_client()
    cursor = db.connection.cursor()
    
    for comment_text in comments_text_to_delete:
        # Find and clear the Player_Comments field for matching replays
        # Use LIKE to match the beginning of the comment
        search_text = comment_text[:30].replace("'", "''")  # Escape quotes
        
        # First find matching replays
        cursor.execute(f"SELECT ReplayId, Player_Comments FROM Replays WHERE Player_Comments LIKE '{search_text}%'")
        matches = cursor.fetchall()
        
        if matches:
            for replay_id, full_comment in matches:
                print(f"  Found ReplayID {replay_id}: {full_comment[:40]}...")
                # Set Player_Comments to NULL
                cursor.execute(f"UPDATE Replays SET Player_Comments = NULL WHERE ReplayId = {replay_id}")
                print(f"  Cleared Player_Comments for ReplayID {replay_id}")
        else:
            print(f"  No matching replay found for: {search_text}...")
    
    db.connection.commit()
    cursor.close()
    print("  Database updated!")
    
except Exception as e:
    print(f"  ERROR updating database: {e}")

print("\n" + "=" * 60)
print("DELETION COMPLETE")
print("=" * 60)



