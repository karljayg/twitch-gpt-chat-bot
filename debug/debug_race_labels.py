import json

with open('data/patterns.json', 'r') as f:
    d = json.load(f)

# Protoss keywords
protoss_keywords = ['adept', 'stalker', 'zealot', 'carrier', 'phoenix', 'oracle', 'void ray', 'colossus', 'archon', 'templar', 'disruptor', 'prism', 'immortal', 'gateway', 'stargate', 'robo', 'nexus', 'pylon', 'probe']

# Find patterns with protoss keywords but wrong race
print("=== Patterns with Protoss keywords but NOT tagged as Protoss ===")
for key in d.keys():
    if key.startswith('pattern_'):
        p = d[key]
        comment = p.get('comment', '').lower()
        race = p.get('race', 'unknown')
        
        if any(kw in comment for kw in protoss_keywords) and race != 'protoss':
            print(f"{key}: '{p.get('comment')}' - tagged as '{race}'")



