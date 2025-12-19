#!/usr/bin/env python3
"""
Comprehensive Learning Data Regeneration Script

This script will:
1. Delete existing data/*.json files (backs them up first)
2. Query all replays from the database where Player_Comments is not NULL
3. Process each replay through the ACTUAL pattern learning system
4. Recreate all learning files (comments.json, patterns.json, learning_stats.json)
5. Use the FIXED player name parsing logic throughout
6. Show detailed progress reports

This serves as both a data cleanup and comprehensive test of our fix.
"""

import sys
import os
import json
import shutil
from datetime import datetime
import time
import io

# Add the project root to the path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.mathison_db import Database
from api.pattern_learning import SC2PatternLearner
from settings import config
import re
import logging

# Global log file handle
_log_file = None

def setup_logging():
    """Set up logging to both console and file"""
    global _log_file
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Create log file with timestamp
    log_filename = f"logs/regenerate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    _log_file = open(log_filename, 'w', encoding='utf-8')
    
    print(f"[LOG] Logging to: {log_filename}")
    _log_file.write(f"=== Learning Data Regeneration Log ===\n")
    _log_file.write(f"Started: {datetime.now().isoformat()}\n\n")
    
    return log_filename

def log_print(message):
    """Print to both console and log file"""
    global _log_file
    
    # Print to console (handle encoding issues on Windows)
    try:
        print(message)
    except UnicodeEncodeError:
        # Replace problematic characters for console
        safe_message = message.encode('ascii', 'replace').decode('ascii')
        print(safe_message)
    
    # Write to log file
    if _log_file:
        _log_file.write(message + '\n')
        _log_file.flush()  # Ensure it's written immediately

def close_logging():
    """Close the log file"""
    global _log_file
    if _log_file:
        _log_file.write(f"\n=== Log completed: {datetime.now().isoformat()} ===\n")
        _log_file.close()
        _log_file = None

class LearningDataRegenerator:
    def __init__(self):
        self.db = Database()
        
        # Set up logging for the pattern learner
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("regenerator")
        
        # Initialize pattern learner (this will create empty data files if they don't exist)
        self.pattern_learner = None
        
    def backup_existing_data(self):
        """Backup existing data files before deletion"""
        log_print("Backing up existing data files...")
        
        backup_dir = f"data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(backup_dir, exist_ok=True)
        
        data_files = ['comments.json', 'patterns.json', 'learning_stats.json', 
                     'comments.json.backup', 'learning_stats.json.backup']
        
        backed_up = 0
        for filename in data_files:
            filepath = os.path.join('data', filename)
            if os.path.exists(filepath):
                backup_path = os.path.join(backup_dir, filename)
                shutil.copy2(filepath, backup_path)
                log_print(f"  [OK] Backed up: {filename}")
                backed_up += 1
        
        log_print(f"Backup completed: {backed_up} files saved to {backup_dir}/")
        return backup_dir
    
    def clear_data_files(self):
        """Delete existing data files to start fresh"""
        log_print("Clearing existing data files...")
        
        data_files = ['comments.json', 'patterns.json', 'learning_stats.json',
                     'comments.json.backup', 'learning_stats.json.backup']
        
        for filename in data_files:
            filepath = os.path.join('data', filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                log_print(f"  [X] Deleted: {filename}")
        
        log_print("Data files cleared!")
    
    def get_replays_with_comments(self):
        """Get all replays from database where Player_Comments is not NULL"""
        try:
            cursor = self.db.connection.cursor(dictionary=True)
            query = """
            SELECT ReplayId, UnixTimestamp, Date_Played, Map, Region, GameDuration,
                   Player1_Race, Player2_Race, Player1_Result, Player2_Result,
                   Replay_Summary, Player_Comments
            FROM Replays 
            WHERE Player_Comments IS NOT NULL 
            ORDER BY Date_Played ASC
            """
            cursor.execute(query)
            replays = cursor.fetchall()
            cursor.close()
            
            log_print(f"Found {len(replays)} replays with player comments")
            return replays
            
        except Exception as e:
            log_print(f"[X] Error querying database: {e}")
            return []
    
    def extract_player_names_from_summary(self, replay_summary):
        """Extract player names using the FIXED parsing logic"""
        try:
            # This is the FIXED regex pattern from models/mathison_db.py
            # OLD BROKEN: r"Players: (\w+[^:]+): (\w+), (\w+[^:]+): (\w+)"
            # NEW FIXED: r"Players: ([^:]+): (\w+), ([^:]+): (\w+)"
            player_matches = re.search(
                r"Players: ([^:]+): (\w+), ([^:]+): (\w+)", replay_summary)
            
            if player_matches:
                player1_name, player1_race, player2_name, player2_race = player_matches.groups()
                return {
                    'player1_name': player1_name.strip(),
                    'player1_race': player1_race.strip(),
                    'player2_name': player2_name.strip(), 
                    'player2_race': player2_race.strip(),
                    'parsing_success': True
                }
            else:
                return {
                    'player1_name': None,
                    'player1_race': None,
                    'player2_name': None,
                    'player2_race': None,
                    'parsing_success': False,
                    'error': 'No player matches found in replay summary'
                }
                
        except Exception as e:
            return {
                'player1_name': None,
                'player1_race': None,
                'player2_name': None,
                'player2_race': None,
                'parsing_success': False,
                'error': str(e)
            }
    
    def extract_build_order_from_summary(self, replay_summary, player_name):
        """Extract build order data from replay summary for a specific player"""
        try:
            build_order = []
            
            # Look for the player's build order section - improved pattern
            # Try multiple pattern variations to catch different formats
            patterns = [
                # Pattern 1: Stop at next player's build order section (most specific)
                rf"{re.escape(player_name)}'s Build Order.*?:\n(.*?)(?:\n\n[A-Z][a-zA-Z]+.*?'s Build Order)",
                # Pattern 2: Stop at other major sections starting with capital letters (but not "Time:")
                rf"{re.escape(player_name)}'s Build Order.*?:\n(.*?)(?:\n\n(?!Time:)[A-Z][a-zA-Z]+)",
                # Pattern 3: Stop at double newline or end
                rf"{re.escape(player_name)}'s Build Order.*?:\n(.*?)(?:\n\n|$)",
            ]
            
            build_match = None
            for i, pattern in enumerate(patterns):
                build_match = re.search(pattern, replay_summary, re.DOTALL | re.IGNORECASE)
                if build_match:
                    log_print(f"    Pattern {i+1} matched")
                    break
            
            if build_match:
                build_text = build_match.group(1)
                log_print(f"    Extracted text length: {len(build_text)} chars")
                log_print(f"    First 200 chars: {build_text[:200]}...")
                
                # Parse each build step: "Time: 0:01, Name: Probe, Supply: 12"
                step_pattern = r"Time: (\d+):(\d+), Name: ([^,]+), Supply: (\d+)"
                steps = re.findall(step_pattern, build_text)
                
                for minute, second, unit_name, supply in steps:
                    time_seconds = int(minute) * 60 + int(second)
                    build_order.append({
                        'supply': int(supply),
                        'name': unit_name.strip(),
                        'time': time_seconds
                    })
            
            return build_order
            
        except Exception as e:
            log_print(f"    [!] Error parsing build order: {e}")
            return []
    
    def detect_comment_about_opponent(self, comment, opponent_name):
        """
        Detect if a comment is describing the opponent's strategy.
        
        IMPORTANT: Player comments are meant to describe what the OPPONENT did.
        This is the core purpose of the pattern learning system - to learn opponent strategies.
        Therefore, we should ALMOST ALWAYS return True (extract opponent's build order).
        
        Only return False if the comment explicitly talks about the streamer's own strategy
        (e.g., "I should have...", "my build was...", "next time I will...")
        """
        try:
            comment_lower = comment.lower()
            
            # Keywords that indicate the comment is about the STREAMER's own strategy
            # These are RARE - most comments are about the opponent
            self_indicators = [
                'i should', 'i need to', 'my build', 'my strategy', 'next time i',
                'i forgot', 'i missed', 'i failed', 'my mistake', 'i played'
            ]
            
            # Only extract streamer's build if explicitly about self
            for indicator in self_indicators:
                if indicator in comment_lower:
                    return False  # Comment is about self, extract streamer's build
            
            # Default: Comments describe opponent strategies, so extract opponent's build
            return True
            
        except Exception as e:
            log_print(f"    [!] Error detecting comment type: {e}")
            return True  # Default to opponent's build on error

    def create_game_data_from_replay(self, replay_record):
        """Create game_data structure from database replay record using FIXED logic"""
        try:
            # Extract player names from replay summary
            parsed_data = self.extract_player_names_from_summary(replay_record['Replay_Summary'])
            
            if not parsed_data['parsing_success']:
                log_print(f"  [!] Failed to parse player names: {parsed_data.get('error', 'Unknown error')}")
                return None
            
            # Create game_player_names string as it would be in the real system
            game_player_names = f"{parsed_data['player1_name']}, {parsed_data['player2_name']}"
            
            # Apply the FIXED logic from _prepare_game_data_for_comment
            game_data = {}
            
            # Get opponent info using FIXED logic
            if config.STREAMER_NICKNAME in game_player_names:
                # Split the comma-separated string into a list first (THE FIX!)
                player_names_list = [name.strip() for name in game_player_names.split(',')]
                opponent_names = [name for name in player_names_list if name != config.STREAMER_NICKNAME]
                if opponent_names:
                    game_data['opponent_name'] = opponent_names[0]
                    
                    # Determine opponent race
                    if game_data['opponent_name'] == parsed_data['player1_name']:
                        game_data['opponent_race'] = parsed_data['player1_race']
                    else:
                        game_data['opponent_race'] = parsed_data['player2_race']
                else:
                    game_data['opponent_name'] = 'Unknown'
                    game_data['opponent_race'] = 'Unknown'
            else:
                log_print(f"  [!] Streamer '{config.STREAMER_NICKNAME}' not found in: {game_player_names}")
                return None
            
            # Determine game result for the streamer
            # Check which player is the streamer and get their result
            if config.STREAMER_NICKNAME == parsed_data['player1_name'] or config.STREAMER_NICKNAME in parsed_data['player1_name']:
                game_data['result'] = replay_record['Player1_Result']
            elif config.STREAMER_NICKNAME == parsed_data['player2_name'] or config.STREAMER_NICKNAME in parsed_data['player2_name']:
                game_data['result'] = replay_record['Player2_Result']
            else:
                # Fallback: assume based on opponent name
                game_data['result'] = 'Victory'  # Default assumption
            
            # Add other game data
            game_data['map'] = replay_record['Map']
            game_data['duration'] = replay_record['GameDuration']
            game_data['date'] = str(replay_record['Date_Played'])
            
            # Determine whose build order to extract based on the comment
            comment = replay_record.get('Player_Comments', '')
            is_about_opponent = self.detect_comment_about_opponent(comment, game_data['opponent_name'])
            
            if is_about_opponent:
                # Extract opponent's build order since comment describes their strategy
                build_order = self.extract_build_order_from_summary(
                    replay_record['Replay_Summary'], 
                    game_data['opponent_name']
                )
                log_print(f"    Comment about opponent - extracting {game_data['opponent_name']}'s build order")
            else:
                # Extract streamer's build order for self-analysis
                build_order = self.extract_build_order_from_summary(
                    replay_record['Replay_Summary'], 
                    config.STREAMER_NICKNAME
                )
                log_print(f"    Comment about own strategy - extracting {config.STREAMER_NICKNAME}'s build order")
            
            game_data['build_order'] = build_order
            game_data['is_about_opponent'] = is_about_opponent
            
            if build_order:
                target_player = game_data['opponent_name'] if is_about_opponent else config.STREAMER_NICKNAME
                log_print(f"    Extracted {len(build_order)} build steps for {target_player}")
            else:
                target_player = game_data['opponent_name'] if is_about_opponent else config.STREAMER_NICKNAME
                log_print(f"    [!] No build order found for {target_player}")
            
            return game_data
            
        except Exception as e:
            log_print(f"  [X] Error creating game data: {str(e)}")
            return None
    
    def regenerate_all_learning_data(self):
        """Main function to regenerate all learning data from database"""
        log_print("Starting Learning Data Regeneration")
        log_print("=" * 70)
        
        # Step 1: Backup existing data
        backup_dir = self.backup_existing_data()
        
        # Step 2: Clear existing data files  
        self.clear_data_files()
        
        # Step 3: Initialize fresh pattern learner
        log_print("Initializing fresh pattern learning system...")
        self.pattern_learner = SC2PatternLearner(self.db, self.logger)
        log_print("  [OK] Pattern learner initialized")
        
        # Step 4: Get all replays with comments
        replays = self.get_replays_with_comments()
        
        if not replays:
            log_print("[X] No replays found with comments. Exiting.")
            return
        
        # Step 5: Process each replay
        log_print(f"\nProcessing {len(replays)} replays...")
        log_print("-" * 70)
        
        success_count = 0
        error_count = 0
        
        for i, replay in enumerate(replays, 1):
            log_print(f"\nReplay {i}/{len(replays)} (ID: {replay['ReplayId']})")
            log_print(f"  Date: {replay['Date_Played']}")
            log_print(f"  Map: {replay['Map']}")
            log_print(f"  Duration: {replay['GameDuration']}")
            log_print(f"  Comment: {replay['Player_Comments'][:60]}{'...' if len(replay['Player_Comments']) > 60 else ''}")
            
            try:
                # Create game data from replay
                game_data = self.create_game_data_from_replay(replay)
                
                if game_data is None:
                    log_print(f"  [X] Failed to create game data")
                    error_count += 1
                    continue
                
                log_print(f"  Opponent: {game_data['opponent_name']} ({game_data['opponent_race']})")
                log_print(f"  Result: {game_data['result']}")
                
                # Process through the pattern learning system
                log_print(f"  Processing through pattern learner...")
                self.pattern_learner._process_new_comment(game_data, replay['Player_Comments'])
                
                log_print(f"  [OK] Successfully processed!")
                success_count += 1
                
                # Show progress every 10 replays
                if i % 10 == 0:
                    log_print(f"\nProgress: {i}/{len(replays)} processed ({success_count} success, {error_count} errors)")
                
            except Exception as e:
                log_print(f"  [X] Error processing replay: {str(e)}")
                error_count += 1
                continue
        
        # Step 6: Final statistics
        log_print("\n" + "=" * 70)
        log_print("REGENERATION COMPLETE!")
        log_print("=" * 70)
        log_print(f"Total replays processed: {len(replays)}")
        log_print(f"[OK] Successful: {success_count}")
        log_print(f"[X] Errors: {error_count}")
        log_print(f"Success rate: {(success_count/len(replays)*100):.1f}%")
        
        # Step 7: Show generated files
        self.show_generated_files()
        
        log_print(f"\nOriginal data backed up to: {backup_dir}/")
        log_print("Learning data regeneration completed successfully!")
        
        return success_count, error_count
    
    def show_generated_files(self):
        """Show information about the generated files"""
        log_print("\nGenerated Learning Files:")
        
        data_files = ['comments.json', 'patterns.json', 'learning_stats.json']
        
        for filename in data_files:
            filepath = os.path.join('data', filename)
            if os.path.exists(filepath):
                size = os.path.getsize(filepath)
                log_print(f"  [OK] {filename}: {size:,} bytes")
                
                # Show some content info
                if filename == 'comments.json':
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                            comment_count = len(data.get('comments', []))
                            keyword_count = len(data.get('keyword_index', {}))
                            log_print(f"       {comment_count} comments, {keyword_count} keywords")
                    except:
                        pass
                elif filename == 'patterns.json':
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                            pattern_count = len(data)
                            log_print(f"       {pattern_count} patterns")
                    except:
                        pass
            else:
                log_print(f"  [X] {filename}: Not generated")
    
def main():
    print("StarCraft 2 Learning Data Regenerator")
    print("=" * 70)
    print("This script will regenerate all learning data from database records")
    print("using the FIXED player name parsing logic.")
    print()
    
    # Confirm with user
    response = input("[!] This will backup and replace all data/*.json files. Continue? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("[X] Operation cancelled by user.")
        return
    
    # Set up logging to file
    log_filename = setup_logging()
    
    try:
        regenerator = LearningDataRegenerator()
        success_count, error_count = regenerator.regenerate_all_learning_data()
        
        if success_count > 0:
            log_print(f"\nRegeneration completed successfully!")
            log_print(f"Processed {success_count} replays with {error_count} errors.")
            
            # Verify the opponent names are now correct
            log_print("\nVerifying opponent names in regenerated data...")
            try:
                with open('data/comments.json', 'r') as f:
                    data = json.load(f)
                    comments = data.get('comments', [])
                    if comments:
                        log_print(f"Sample opponent names from regenerated data:")
                        for i, comment in enumerate(comments[:5]):
                            opponent = comment.get('game_data', {}).get('opponent_name', 'Unknown')
                            comment_text = comment.get('comment', '')[:40]
                            log_print(f"   {i+1}. {opponent} - \"{comment_text}...\"")
                    else:
                        log_print("[!] No comments found in regenerated data")
            except Exception as e:
                log_print(f"[!] Could not verify data: {e}")
        else:
            log_print(f"\n[X] No replays were successfully processed.")
        
        log_print(f"\nFull log saved to: {log_filename}")
            
    except Exception as e:
        log_print(f"\nScript failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        close_logging()

if __name__ == "__main__":
    main()
