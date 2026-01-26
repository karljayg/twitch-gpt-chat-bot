import json

# Check backup
with open('data_backup_20251218_150439/patterns.json', 'r') as f:
    d = json.load(f)

protoss_keywords = ['adept', 'stalker', 'zealot', 'carrier', 'phoenix', 'oracle', 'void ray', 'colossus', 'archon', 'templar', 'gateway', 'stargate', 'prism', 'immortal']

print("=== BACKUP patterns.json (150439) - checking race labels ===")
wrong_count = 0
for key in list(d.keys())[:100]:
    if key.startswith('pattern_'):
        p = d[key]
        comment = p.get('comment', '').lower()
        race = p.get('race', 'unknown')
        
        if any(kw in comment for kw in protoss_keywords) and race != 'protoss':
            wrong_count += 1
            if wrong_count <= 10:
                print(f"{key}: '{p.get('comment')[:50]}...' - tagged as '{race}'")

print(f"\nTotal wrong Protoss labels in first 100 patterns: {wrong_count}")



