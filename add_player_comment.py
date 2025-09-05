#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.pattern_learning import SC2PatternLearner
from models.mathison_db import Database
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Command-line interface for adding player comments"""
    print("🎮 Player Comment Manager")
    print("=" * 50)
    
    try:
        # Create database and pattern learner
        db = Database()
        pattern_learner = SC2PatternLearner(db, logger)
        
        if len(sys.argv) < 2:
            show_usage()
            return
        
        command = sys.argv[1].lower()
        
        if command == "list":
            # List recent games that could benefit from comments
            recent_games = pattern_learner.list_recent_games_for_comment(limit=20)
            
            if recent_games:
                print(f"\n📋 Recent games needing player comments ({len(recent_games)} found):")
                print("-" * 80)
                for i, game in enumerate(recent_games, 1):
                    print(f"{i:2d}. {game['opponent']} ({game['race']}) on {game['map']}")
                    print(f"    Date: {game['date']}")
                    print(f"    AI Comment: {game['ai_comment']} (Confidence: {game['confidence']:.1%})")
                    print()
            else:
                print("✅ All recent games already have player comments!")
        
        elif command == "add":
            # Add a comment for a specific game
            if len(sys.argv) < 6:
                print("❌ Usage: python add_player_comment.py add <opponent> <map> <date> <comment>")
                print("   Example: python add_player_comment.py add DKeyAbuser \"Royal Blood LE\" \"2025-09-01 23:45\" \"cannon rush into DT\"")
                return
            
            opponent = sys.argv[2]
            map_name = sys.argv[3]
            date = sys.argv[4]
            comment = " ".join(sys.argv[5:])
            
            print(f"📝 Adding comment for {opponent} on {map_name}...")
            success = pattern_learner.add_player_comment_later(opponent, map_name, date, comment)
            
            if success:
                print(f"✅ Comment added successfully: {comment}")
            else:
                print(f"❌ Failed to add comment. Game not found or error occurred.")
        
        elif command == "edit":
            # Edit an AI comment with a player comment
            if len(sys.argv) < 6:
                print("❌ Usage: python add_player_comment.py edit <opponent> <map> <date> <new_comment>")
                print("   Example: python add_player_comment.py edit DKeyAbuser \"Royal Blood LE\" \"2025-09-01 23:45\" \"cannon rush into DT to collosus\"")
                return
            
            opponent = sys.argv[2]
            map_name = sys.argv[3]
            date = sys.argv[4]
            new_comment = " ".join(sys.argv[5:])
            
            print(f"✏️  Editing comment for {opponent} on {map_name}...")
            success = pattern_learner.edit_ai_comment(opponent, map_name, date, new_comment)
            
            if success:
                print(f"✅ Comment edited successfully: {new_comment}")
            else:
                print(f"❌ Failed to edit comment. Game not found or error occurred.")
        
        elif command == "help":
            show_usage()
        
        else:
            print(f"❌ Unknown command: {command}")
            show_usage()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def show_usage():
    """Show usage instructions"""
    print("\n📖 Usage:")
    print("  python add_player_comment.py <command> [options]")
    print("\n🔧 Commands:")
    print("  list                    - Show recent games needing player comments")
    print("  add <opp> <map> <date> <comment>  - Add comment to a game")
    print("  edit <opp> <map> <date> <comment> - Replace AI comment with player comment")
    print("  help                    - Show this help message")
    print("\n📝 Examples:")
    print("  python add_player_comment.py list")
    print("  python add_player_comment.py add DKeyAbuser \"Royal Blood LE\" \"2025-09-01 23:45\" \"cannon rush into DT\"")
    print("  python add_player_comment.py edit DKeyAbuser \"Royal Blood LE\" \"2025-09-01 23:45\" \"cannon rush into DT to collosus\"")
    print("\n💡 Tips:")
    print("  - Use 'list' to see which games need comments")
    print("  - Dates can be approximate (within 1 day)")
    print("  - Map names should match what's in the replay data")
    print("  - Comments will be processed for keywords and patterns")

if __name__ == "__main__":
    main()
