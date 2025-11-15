"""
Validation script to check if build orders in patterns.json and database
were incorrectly attributed to the wrong player due to case-sensitivity bug.

This checks if builds contain units/buildings from the correct race.
"""

import json
import sys
from datetime import datetime, timedelta
from models.mathison_db import Database
from settings import config

# Define race-specific units and buildings
RACE_UNITS = {
    'Protoss': {
        'workers': ['Probe'],
        'buildings': ['Nexus', 'Pylon', 'Gateway', 'CyberneticsCore', 'Forge', 'PhotonCannon',
                     'Stargate', 'RoboticsFacility', 'TwilightCouncil', 'TemplarArchive',
                     'DarkShrine', 'RoboticsBay', 'FleetBeacon', 'Assimilator', 'WarpGate',
                     'ShieldBattery'],
        'units': ['Zealot', 'Stalker', 'Sentry', 'Adept', 'High Templar', 'Dark Templar',
                 'Archon', 'Observer', 'Warp Prism', 'Immortal', 'Colossus', 'Disruptor',
                 'Phoenix', 'Void Ray', 'Oracle', 'Tempest', 'Carrier', 'Mothership']
    },
    'Terran': {
        'workers': ['SCV'],
        'buildings': ['CommandCenter', 'SupplyDepot', 'Barracks', 'Factory', 'Starport',
                     'EngineeringBay', 'Armory', 'MissileTurret', 'Bunker', 'SensorTower',
                     'GhostAcademy', 'FusionCore', 'TechLab', 'Reactor', 'Refinery',
                     'OrbitalCommand', 'PlanetaryFortress'],
        'units': ['Marine', 'Marauder', 'Reaper', 'Ghost', 'Hellion', 'Hellbat', 'Widow Mine',
                 'Cyclone', 'Siege Tank', 'Thor', 'Viking', 'Medivac', 'Liberator', 'Raven',
                 'Banshee', 'Battlecruiser']
    },
    'Zerg': {
        'workers': ['Drone'],
        'buildings': ['Hatchery', 'Lair', 'Hive', 'Extractor', 'SpawningPool', 'EvolutionChamber',
                     'RoachWarren', 'BanelingNest', 'SpineCrawler', 'SporeCrawler',
                     'HydraliskDen', 'LurkerDen', 'InfestationPit', 'Spire', 'NydusNetwork',
                     'UltraliskCavern', 'GreaterSpire', 'CreepTumor', 'CreepTumorBurrowed'],
        'units': ['Queen', 'Zergling', 'Baneling', 'Roach', 'Ravager', 'Hydralisk', 'Lurker',
                 'LurkerBurrowed', 'Infestor', 'Swarm Host', 'Mutalisk', 'Corruptor',
                 'Viper', 'Ultralisk', 'Brood Lord', 'Overlord', 'Overseer', 'Changeling']
    }
}

def get_all_race_identifiers(race):
    """Get all unit/building names for a race"""
    if race not in RACE_UNITS:
        return set()
    race_data = RACE_UNITS[race]
    return set(race_data['workers'] + race_data['buildings'] + race_data['units'])

def analyze_build_order(build_order, expected_race):
    """
    Analyze a build order to see if it matches the expected race.
    Returns (is_correct, detected_race, details)
    """
    if not build_order:
        return True, 'Unknown', "Empty build order"
    
    # Count units from each race
    race_counts = {'Protoss': 0, 'Terran': 0, 'Zerg': 0}
    unit_list = []
    
    # Parse build order (could be list of dicts or list of strings)
    for item in build_order:
        unit_name = None
        if isinstance(item, dict):
            unit_name = item.get('name', '')
        elif isinstance(item, str):
            # Parse string format: "Name: X, Supply: Y" or just "X"
            if 'Name:' in item:
                parts = item.split(',')
                for part in parts:
                    if 'Name:' in part:
                        unit_name = part.split('Name:')[1].strip()
                        break
            else:
                unit_name = item.strip()
        
        if unit_name:
            unit_list.append(unit_name)
            # Check which race this unit belongs to
            for race, identifiers in [(r, get_all_race_identifiers(r)) for r in ['Protoss', 'Terran', 'Zerg']]:
                if unit_name in identifiers:
                    race_counts[race] += 1
    
    # Determine detected race (the one with most units)
    if sum(race_counts.values()) == 0:
        return True, 'Unknown', "No recognizable units found"
    
    detected_race = max(race_counts, key=race_counts.get)
    
    # Check if detected race matches expected race
    is_correct = (detected_race == expected_race) if expected_race != 'Unknown' else True
    
    details = f"Race counts: {race_counts}, Sample units: {unit_list[:5]}"
    return is_correct, detected_race, details

def validate_patterns_json():
    """Validate patterns in patterns.json"""
    print("\n" + "="*60)
    print("VALIDATING PATTERNS.JSON")
    print("="*60)
    
    try:
        with open('data/patterns.json', 'r') as f:
            patterns_data = json.load(f)
    except FileNotFoundError:
        print("patterns.json not found - skipping validation")
        return []
    except json.JSONDecodeError as e:
        print(f"Error reading patterns.json: {e}")
        return []
    
    issues = []
    total_patterns = 0
    correct_count = 0
    
    for opponent_name, opponent_data in patterns_data.items():
        if not isinstance(opponent_data, dict):
            continue
            
        opponent_race = opponent_data.get('race', 'Unknown')
        games = opponent_data.get('games', [])
        
        # Skip placeholder patterns with no games
        if not games or len(games) == 0:
            continue
        
        print(f"\nChecking opponent: {opponent_name} ({opponent_race}) - {len(games)} games")
        
        for game_idx, game in enumerate(games):
            total_patterns += 1
            build_order = game.get('build_order', [])
            game_date = game.get('date', 'Unknown')
            game_map = game.get('map', 'Unknown')
            
            is_correct, detected_race, details = analyze_build_order(build_order, opponent_race)
            
            if not is_correct:
                        issue = {
                            'type': 'patterns.json',
                            'opponent': opponent_name,
                            'expected_race': opponent_race,
                            'detected_race': detected_race,
                            'date': game_date,
                            'map': game_map,
                            'details': details,
                            'game_index': game_idx
                        }
                        issues.append(issue)
                        print(f"  [{total_patterns}] [X] MISMATCH - Expected {opponent_race}, detected {detected_race} ({game_date})")
            else:
                        correct_count += 1
                        print(f"  [{total_patterns}] [OK] - {opponent_race} ({game_date})")
    
    print(f"\n{'-'*60}")
    print(f"Patterns.json Summary: {correct_count} correct, {len(issues)} issues out of {total_patterns} total")
    print(f"{'-'*60}")
    
    return issues

def validate_database(days=4):
    """Validate recent database entries"""
    print("\n" + "="*60)
    print(f"VALIDATING DATABASE (Last {days} days)")
    print("="*60)
    
    try:
        db = Database()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return []
    
    # Get recent replays
    cutoff_date = datetime.now() - timedelta(days=days)
    
    try:
        # Query for recent 1v1 games using database cursor with dictionary=True
        query = """
            SELECT 
                p1.SC2_UserId AS Player1_Name,
                r.Player1_Race,
                p2.SC2_UserId AS Player2_Name,
                r.Player2_Race,
                r.Date_Played,
                r.Map,
                r.Replay_Summary,
                r.GameType
            FROM Replays r
            JOIN Players p1 ON r.Player1_Id = p1.Id
            JOIN Players p2 ON r.Player2_Id = p2.Id
            WHERE r.Date_Played >= %s
            AND r.GameType = '1v1'
            ORDER BY r.Date_Played DESC
        """
        
        conn = db.ensure_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)
        cursor.execute(query, (cutoff_date,))
        results = cursor.fetchall()
        
        if not results:
            print("No recent games found in database")
            return []
        
        issues = []
        total_games = len(results)
        correct_count = 0
        player_accounts_lower = [name.lower() for name in config.SC2_PLAYER_ACCOUNTS]
        
        print(f"\nProcessing {total_games} games from database...")
        
        for idx, row in enumerate(results, 1):
            player1_name = row['Player1_Name']
            player1_race = row['Player1_Race']
            player2_name = row['Player2_Name']
            player2_race = row['Player2_Race']
            date_played = row['Date_Played']
            game_map = row['Map']
            replay_summary = row['Replay_Summary']
            
            # Determine who is the streamer and who is the opponent
            if player1_name.lower() in player_accounts_lower:
                streamer_name = player1_name
                streamer_race = player1_race
                opponent_name = player2_name
                opponent_race = player2_race
            elif player2_name.lower() in player_accounts_lower:
                streamer_name = player2_name
                streamer_race = player2_race
                opponent_name = player1_name
                opponent_race = player1_race
            else:
                # Neither player is the streamer (shouldn't happen, but skip)
                print(f"  [{idx}/{total_games}] [!] SKIPPED - Neither player is streamer")
                continue
            
            # Parse build orders from replay_summary
            if replay_summary:
                # Extract opponent's build order from summary
                opponent_build = []
                in_opponent_build = False
                
                for line in replay_summary.split('\n'):
                    if f"{opponent_name}'s Build Order" in line:
                        in_opponent_build = True
                        continue
                    elif "'s Build Order" in line and opponent_name not in line:
                        in_opponent_build = False
                    elif in_opponent_build and line.strip().startswith("Time:"):
                        opponent_build.append(line.strip())
                
                if opponent_build:
                    is_correct, detected_race, details = analyze_build_order(opponent_build, opponent_race)
                    
                    if not is_correct:
                        issue = {
                            'type': 'database',
                            'opponent': opponent_name,
                            'expected_race': opponent_race,
                            'detected_race': detected_race,
                            'date': str(date_played),
                            'map': game_map,
                            'details': details,
                            'streamer': streamer_name,
                            'streamer_race': streamer_race
                        }
                        issues.append(issue)
                        print(f"  [{idx}/{total_games}] [X] MISMATCH - {opponent_name}: Expected {opponent_race}, detected {detected_race} ({date_played})")
                    else:
                        correct_count += 1
                        print(f"  [{idx}/{total_games}] [OK] - {opponent_name} vs {streamer_name}: {opponent_race} ({date_played})")
                else:
                    print(f"  [{idx}/{total_games}] [!] NO BUILD - {opponent_name} ({date_played})")
            else:
                print(f"  [{idx}/{total_games}] [!] NO SUMMARY - {opponent_name} ({date_played})")
        
        print(f"\n{'-'*60}")
        print(f"Database Summary: {correct_count} correct, {len(issues)} issues out of {total_games} games")
        print(f"{'-'*60}")
        
        return issues
        
    except Exception as e:
        print(f"Error querying database: {e}")
        import traceback
        traceback.print_exc()
        return []

def main():
    print("\n" + "="*60)
    print("BUILD ORDER VALIDATION SCRIPT")
    print("Checking for incorrect race attribution due to case-sensitivity bug")
    print("="*60)
    
    # Validate patterns.json
    pattern_issues = validate_patterns_json()
    
    # Validate database (last 4 days)
    db_issues = validate_database(days=4)
    
    # Summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    print(f"Total issues found in patterns.json: {len(pattern_issues)}")
    print(f"Total issues found in database: {len(db_issues)}")
    print(f"Total issues: {len(pattern_issues) + len(db_issues)}")
    
    if pattern_issues or db_issues:
        print("\n[!] Issues detected! Review the output above for details.")
        print("\nNext steps:")
        print("1. The case-sensitivity bug has been fixed in the code")
        print("2. Consider cleaning corrupted patterns from patterns.json")
        print("3. Database entries may need manual review")
        
        # Save issues to file
        with open('validation_results.txt', 'w', encoding='utf-8') as f:
            f.write("BUILD ORDER VALIDATION RESULTS\n")
            f.write("="*60 + "\n\n")
            
            f.write(f"Patterns.json issues: {len(pattern_issues)}\n")
            for issue in pattern_issues:
                f.write(f"\n{json.dumps(issue, indent=2)}\n")
            
            f.write(f"\n\nDatabase issues: {len(db_issues)}\n")
            for issue in db_issues:
                f.write(f"\n{json.dumps(issue, indent=2)}\n")
        
        print("\n[OK] Detailed results saved to: validation_results.txt")
    else:
        print("\n[OK] No issues found! All build orders match expected races.")
    
    return 0 if not (pattern_issues or db_issues) else 1

if __name__ == '__main__':
    sys.exit(main())

