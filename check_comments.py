#!/usr/bin/env python3

from models.mathison_db import Database

def check_player_comments():
    db = Database()
    cursor = db.cursor
    
    try:
        # Count total replays with comments
        cursor.execute("SELECT COUNT(*) as total_replays FROM Replays WHERE Player_Comments IS NOT NULL")
        result = cursor.fetchone()
        total_with_comments = result["total_replays"]
        
        print(f"Total replays with player comments: {total_with_comments}")
        
        if total_with_comments > 0:
            # Get sample of recent comments
            cursor.execute("""
                SELECT Player_Comments, Map, Date_Played, GameDuration 
                FROM Replays 
                WHERE Player_Comments IS NOT NULL 
                ORDER BY Date_Played DESC 
                LIMIT 10
            """)
            results = cursor.fetchall()
            
            print("\nSample of recent comments:")
            for r in results:
                print(f"{r['Date_Played']} - {r['Map']} ({r['GameDuration']}): {r['Player_Comments']}")
        
        # Get total replays for comparison
        cursor.execute("SELECT COUNT(*) as total FROM Replays")
        total_replays = cursor.fetchone()["total"]
        print(f"\nTotal replays in database: {total_replays}")
        print(f"Percentage with comments: {(total_with_comments/total_replays)*100:.1f}%")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_player_comments()
