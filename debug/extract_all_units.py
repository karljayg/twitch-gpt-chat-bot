"""Extract all unique unit/building names from patterns and comments to ensure config is complete"""
import json
from collections import defaultdict

# We'll categorize by what race they belong to
zerg_items = set()
terran_items = set()
protoss_items = set()
unknown_items = set()

# Known race mappings for SC2 units/buildings
RACE_MAP = {
    # Zerg
    'drone': 'zerg', 'overlord': 'zerg', 'zergling': 'zerg', 'queen': 'zerg',
    'hatchery': 'zerg', 'spawningpool': 'zerg', 'extractor': 'zerg', 'lair': 'zerg', 'hive': 'zerg',
    'roach': 'zerg', 'roachwarren': 'zerg', 'baneling': 'zerg', 'banelingnest': 'zerg',
    'hydralisk': 'zerg', 'hydraliskden': 'zerg', 'mutalisk': 'zerg', 'spire': 'zerg', 'greaterspire': 'zerg',
    'corruptor': 'zerg', 'broodlord': 'zerg', 'ultralisk': 'zerg', 'ultraliskcavern': 'zerg',
    'infestor': 'zerg', 'infestationpit': 'zerg', 'swarmhost': 'zerg', 'viper': 'zerg',
    'lurker': 'zerg', 'lurkerden': 'zerg', 'ravager': 'zerg', 'overseer': 'zerg',
    'spinecrawler': 'zerg', 'sporecrawler': 'zerg', 'evolutionchamber': 'zerg',
    'nydusnetwork': 'zerg', 'nydusworm': 'zerg', 'changeling': 'zerg',
    'metabolicboost': 'zerg', 'adrenalglands': 'zerg', 'pneumatizedcarapace': 'zerg',
    'glialreconstitution': 'zerg', 'tunnelingclaws': 'zerg', 'burrow': 'zerg',
    'groovedspines': 'zerg', 'muscularaugments': 'zerg', 'chitinousplating': 'zerg',
    'anabolicsynthesis': 'zerg', 'adaptivetalons': 'zerg', 'seismicspines': 'zerg',
    'zergmeleeweaponslevel1': 'zerg', 'zergmeleeweaponslevel2': 'zerg', 'zergmeleeweaponslevel3': 'zerg',
    'zergmissileweaponslevel1': 'zerg', 'zergmissileweaponslevel2': 'zerg', 'zergmissileweaponslevel3': 'zerg',
    'zerggroundarmorslevel1': 'zerg', 'zerggroundarmorslevel2': 'zerg', 'zerggroundarmorslevel3': 'zerg',
    'zergflyerweaponslevel1': 'zerg', 'zergflyerweaponslevel2': 'zerg', 'zergflyerweaponslevel3': 'zerg',
    'zergflyerarmorslevel1': 'zerg', 'zergflyerarmorslevel2': 'zerg', 'zergflyerarmorslevel3': 'zerg',
    
    # Terran
    'scv': 'terran', 'marine': 'terran', 'marauder': 'terran', 'reaper': 'terran', 'ghost': 'terran',
    'commandcenter': 'terran', 'orbitalcommand': 'terran', 'planetaryfortress': 'terran',
    'supplydepot': 'terran', 'refinery': 'terran', 'barracks': 'terran', 'factory': 'terran', 'starport': 'terran',
    'engineeringbay': 'terran', 'armory': 'terran', 'ghostacademy': 'terran', 'fusioncore': 'terran',
    'techlab': 'terran', 'reactor': 'terran', 'bunker': 'terran', 'missileturret': 'terran', 'sensortower': 'terran',
    'hellion': 'terran', 'hellbat': 'terran', 'widowmine': 'terran', 'siegetank': 'terran', 'cyclone': 'terran', 'thor': 'terran',
    'viking': 'terran', 'medivac': 'terran', 'liberator': 'terran', 'banshee': 'terran', 'raven': 'terran', 'battlecruiser': 'terran',
    'mule': 'terran', 'autoturret': 'terran',
    'stimpack': 'terran', 'combatshield': 'terran', 'combatshields': 'terran', 'concussiveshells': 'terran',
    'siegetech': 'terran', 'infernalpreigniter': 'terran', 'drillingclaws': 'terran', 'smartservos': 'terran',
    'bansheecloak': 'terran', 'hyperflightrotors': 'terran', 'magfieldaccelerator': 'terran',
    'rapidreignitionsystem': 'terran', 'advancedballistics': 'terran', 'yamatocannon': 'terran',
    'hisecautotracking': 'terran', 'neosteelframe': 'terran', 'neosteelarmor': 'terran', 'buildingarmor': 'terran',
    'terraninfantryweaponslevel1': 'terran', 'terraninfantryweaponslevel2': 'terran', 'terraninfantryweaponslevel3': 'terran',
    'terraninfantryarmorslevel1': 'terran', 'terraninfantryarmorslevel2': 'terran', 'terraninfantryarmorslevel3': 'terran',
    'terranvehicleweaponslevel1': 'terran', 'terranvehicleweaponslevel2': 'terran', 'terranvehicleweaponslevel3': 'terran',
    'terranvehicleplatinglevel1': 'terran', 'terranvehicleplatinglevel2': 'terran', 'terranvehicleplatinglevel3': 'terran',
    'terranshipweaponslevel1': 'terran', 'terranshipweaponslevel2': 'terran', 'terranshipweaponslevel3': 'terran',
    'terranshipplatinglevel1': 'terran', 'terranshipplatinglevel2': 'terran', 'terranshipplatinglevel3': 'terran',
    
    # Protoss
    'probe': 'protoss', 'zealot': 'protoss', 'stalker': 'protoss', 'sentry': 'protoss', 'adept': 'protoss',
    'hightemplar': 'protoss', 'darktemplar': 'protoss', 'archon': 'protoss',
    'nexus': 'protoss', 'pylon': 'protoss', 'assimilator': 'protoss', 'gateway': 'protoss', 'warpgate': 'protoss',
    'forge': 'protoss', 'cyberneticscore': 'protoss', 'twilightcouncil': 'protoss',
    'roboticsfacility': 'protoss', 'roboticsbay': 'protoss', 'stargate': 'protoss', 'fleetbeacon': 'protoss',
    'templararchive': 'protoss', 'darkshrine': 'protoss', 'photoncannon': 'protoss', 'shieldbattery': 'protoss',
    'immortal': 'protoss', 'colossus': 'protoss', 'disruptor': 'protoss', 'observer': 'protoss', 'warpprism': 'protoss',
    'phoenix': 'protoss', 'oracle': 'protoss', 'voidray': 'protoss', 'tempest': 'protoss', 'carrier': 'protoss', 'mothership': 'protoss',
    'interceptor': 'protoss',
    'warpgateresearch': 'protoss', 'charge': 'protoss', 'blink': 'protoss', 'resonatingglaives': 'protoss',
    'shadowstride': 'protoss', 'psistorm': 'protoss', 'extendedthermallance': 'protoss',
    'graviticdrive': 'protoss', 'graviticboosters': 'protoss', 'fluxvanes': 'protoss', 'anionpulsecrystals': 'protoss',
    'protossgroundweaponslevel1': 'protoss', 'protossgroundweaponslevel2': 'protoss', 'protossgroundweaponslevel3': 'protoss',
    'protossgroundarmorslevel1': 'protoss', 'protossgroundarmorslevel2': 'protoss', 'protossgroundarmorslevel3': 'protoss',
    'protossshieldslevel1': 'protoss', 'protossshieldslevel2': 'protoss', 'protossshieldslevel3': 'protoss',
    'protossairweaponslevel1': 'protoss', 'protossairweaponslevel2': 'protoss', 'protossairweaponslevel3': 'protoss',
    'protossairarmorslevel1': 'protoss', 'protossairarmorslevel2': 'protoss', 'protossairarmorslevel3': 'protoss',
}

def normalize_name(name):
    """Normalize unit name for comparison"""
    return name.lower().replace(' ', '').replace('_', '').replace('-', '')

def get_race(name):
    """Determine race from unit/building name"""
    normalized = normalize_name(name)
    return RACE_MAP.get(normalized, 'unknown')

# Load patterns
print("Loading patterns.json...")
with open('data/patterns.json', 'r', encoding='utf-8') as f:
    patterns = json.load(f)

# Load comments
print("Loading comments.json...")
with open('data/comments.json', 'r', encoding='utf-8') as f:
    comments_data = json.load(f)

all_items = defaultdict(set)

# Extract from patterns
print(f"Processing {len(patterns)} patterns...")
for name, pattern in patterns.items():
    sig = pattern.get('signature', {})
    race = pattern.get('race', 'unknown').lower()
    
    for item in sig.get('early_game', []):
        unit_name = item.get('unit', item.get('name', ''))
        if unit_name:
            item_race = get_race(unit_name)
            if item_race == 'unknown':
                item_race = race  # Use pattern's race as fallback
            all_items[item_race].add(unit_name)
    
    for key in sig.get('key_timings', {}):
        item_race = get_race(key)
        if item_race == 'unknown':
            item_race = race
        all_items[item_race].add(key)

# Extract from comments
print(f"Processing {len(comments_data.get('comments', []))} comments...")
for comment in comments_data.get('comments', []):
    game_data = comment.get('game_data', {})
    race = game_data.get('opponent_race', 'unknown').lower()
    build_order = game_data.get('build_order', [])
    
    for step in build_order:
        unit_name = step.get('name', '')
        if unit_name:
            item_race = get_race(unit_name)
            if item_race == 'unknown':
                item_race = race
            all_items[item_race].add(unit_name)

# Print results
print("\n" + "=" * 70)
print("ALL UNIQUE ITEMS FOUND IN YOUR REPLAY DATA")
print("=" * 70)

for race in ['zerg', 'terran', 'protoss', 'unknown']:
    items = sorted(all_items.get(race, []))
    if items:
        print(f"\n{race.upper()} ({len(items)} items):")
        
        # Categorize
        buildings = []
        units = []
        upgrades = []
        
        for item in items:
            normalized = normalize_name(item)
            # Rough categorization
            if any(x in normalized for x in ['level1', 'level2', 'level3', 'boost', 'glands', 'claws', 
                   'carapace', 'weapons', 'armor', 'shields', 'charge', 'blink', 'stimpack', 'shield',
                   'tech', 'servos', 'cloak', 'rotors', 'accelerator', 'research', 'glaives', 'lance',
                   'spines', 'augments', 'plating', 'reconstitution', 'burrow', 'drive', 'crystals']):
                upgrades.append(item)
            elif any(x in normalized for x in ['hatchery', 'lair', 'hive', 'pool', 'warren', 'nest', 'spire', 
                    'den', 'pit', 'cavern', 'chamber', 'crawler', 'network', 'extractor',
                    'command', 'depot', 'refinery', 'barracks', 'factory', 'starport', 'bay', 'armory',
                    'academy', 'core', 'lab', 'reactor', 'bunker', 'turret', 'sensor', 'fortress',
                    'nexus', 'pylon', 'assimilator', 'gateway', 'warpgate', 'forge', 'council', 'shrine',
                    'facility', 'beacon', 'archive', 'cannon', 'battery']):
                buildings.append(item)
            else:
                units.append(item)
        
        if buildings:
            print(f"  Buildings: {', '.join(sorted(buildings))}")
        if units:
            print(f"  Units: {', '.join(sorted(units))}")
        if upgrades:
            print(f"  Upgrades: {', '.join(sorted(upgrades))}")

print("\n" + "=" * 70)
print("Copy the above into settings/config.py SC2_STRATEGIC_ITEMS")
print("=" * 70)



