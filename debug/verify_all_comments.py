"""
Verify all player comments return 100% similarity when matched against themselves.
Also shows top related patterns for review.
"""
import json
import sys
import os
from datetime import datetime

sys.path.insert(0, '.')
from api.ml_opponent_analyzer import MLOpponentAnalyzer
from settings import config

def main():
    # Setup output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"logs/verify_comments_{timestamp}.txt"
    os.makedirs("logs", exist_ok=True)
    
    analyzer = MLOpponentAnalyzer()
    
    # Load comments
    with open('data/comments.json', 'r') as f:
        comments_data = json.load(f)
    comments = comments_data.get('comments', [])
    
    # Load patterns
    with open('data/patterns.json', 'r') as f:
        patterns_data = json.load(f)
    
    results = []
    perfect_matches = 0
    high_matches = 0  # 90%+
    medium_matches = 0  # 70-89%
    low_matches = 0  # <70%
    no_build = 0
    corrupted_build = 0
    
    # Race-specific units to detect wrong player
    zerg_units = {'drone', 'overlord', 'hatchery', 'spawningpool', 'extractor', 'zergling', 'queen'}
    terran_units = {'scv', 'supplydepot', 'barracks', 'refinery', 'commandcenter', 'marine'}
    protoss_units = {'probe', 'pylon', 'gateway', 'assimilator', 'nexus', 'zealot'}
    
    print(f"Verifying {len(comments)} comments...")
    print(f"Output will be saved to: {output_file}")
    print()
    
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write("=" * 80 + "\n")
        out.write(f"PATTERN MATCHING VERIFICATION REPORT\n")
        out.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        out.write(f"Total comments to verify: {len(comments)}\n")
        out.write("=" * 80 + "\n\n")
        
        for idx, comment in enumerate(comments):
            game_data = comment.get('game_data', {})
            build_order = game_data.get('build_order', [])
            comment_text = comment.get('comment', '')[:60]
            opponent = game_data.get('opponent_name', 'Unknown')
            race = game_data.get('opponent_race', 'Unknown')
            map_name = game_data.get('map', 'Unknown')
            date = game_data.get('date', 'Unknown')
            
            if not build_order:
                no_build += 1
                continue
            
            # Check for corrupted build order (wrong player)
            first_units = set(s.get('name', '').lower() for s in build_order[:10])
            race_lower = race.lower()
            is_corrupted = False
            if race_lower == 'terran' and (first_units & zerg_units or first_units & protoss_units):
                is_corrupted = True
            elif race_lower == 'protoss' and (first_units & zerg_units or first_units & terran_units):
                is_corrupted = True
            elif race_lower == 'zerg' and (first_units & terran_units or first_units & protoss_units):
                is_corrupted = True
            
            # Match against comments.json (Pattern Learning)
            comment_matches = analyzer.match_build_against_all_patterns(
                build_order, race, logger=None
            )
            
            # Match against patterns.json (ML Analysis)
            pattern_matches = analyzer._match_build_against_patterns(
                build_order, patterns_data, race, logger=None
            )
            
            # Find self-match score
            self_score_comments = 0
            self_score_patterns = 0
            in_patterns = False
            
            for m in comment_matches:
                if m.get('comment', '')[:50] == comment_text[:50]:
                    self_score_comments = m.get('similarity', 0)
                    break
            
            for m in pattern_matches:
                if m.get('comment', '')[:50] == comment_text[:50]:
                    self_score_patterns = m.get('similarity', 0)
                    in_patterns = True
                    break
            
            # Categorize based on comments.json match (always exists)
            # patterns.json may not have all entries
            if is_corrupted:
                corrupted_build += 1
                status = "CORRUPTED (wrong player build)"
            elif self_score_comments >= 0.99:
                perfect_matches += 1
                status = "PERFECT"
            elif self_score_comments >= 0.90:
                high_matches += 1
                status = "HIGH"
            elif self_score_comments >= 0.70:
                medium_matches += 1
                status = "MEDIUM"
            else:
                low_matches += 1
                status = "LOW"
            
            # Add pattern status
            if not in_patterns:
                status += " (not in patterns.json)"
            
            # Write to report
            out.write("-" * 80 + "\n")
            out.write(f"Comment #{idx + 1}: '{comment_text}'\n")
            out.write(f"Opponent: {opponent} ({race}) on {map_name} - {date}\n")
            out.write(f"Build steps: {len(build_order)}\n")
            out.write(f"Self-match: Comments={self_score_comments:.0%}, Patterns={self_score_patterns:.0%} [{status}]\n")
            out.write("\n")
            
            # Top 5 similar from comments.json
            out.write("Pattern Learning (comments.json) - Top 5:\n")
            for i, m in enumerate(comment_matches[:5]):
                is_self = "(SELF)" if m.get('comment', '')[:50] == comment_text[:50] else ""
                out.write(f"  {i+1}. {m.get('similarity', 0):.0%} - '{m.get('comment', '')[:55]}' {is_self}\n")
            
            out.write("\n")
            
            # Top 5 similar from patterns.json
            out.write("ML Analysis (patterns.json) - Top 5:\n")
            for i, m in enumerate(pattern_matches[:5]):
                is_self = "(SELF)" if m.get('comment', '')[:50] == comment_text[:50] else ""
                out.write(f"  {i+1}. {m.get('similarity', 0):.0%} - '{m.get('comment', '')[:55]}' {is_self}\n")
            
            out.write("\n")
            
            # Progress
            if (idx + 1) % 50 == 0:
                print(f"  Processed {idx + 1}/{len(comments)}...")
        
        # Summary
        out.write("=" * 80 + "\n")
        out.write("SUMMARY\n")
        out.write("=" * 80 + "\n")
        out.write(f"Total comments: {len(comments)}\n")
        out.write(f"Comments with build order: {len(comments) - no_build}\n")
        out.write(f"Comments without build order: {no_build}\n")
        out.write("\n")
        out.write(f"Self-match results:\n")
        out.write(f"  PERFECT (100%): {perfect_matches}\n")
        out.write(f"  HIGH (90-99%): {high_matches}\n")
        out.write(f"  MEDIUM (70-89%): {medium_matches}\n")
        out.write(f"  LOW (<70%): {low_matches}\n")
        out.write(f"  CORRUPTED (wrong player build): {corrupted_build}\n")
        out.write("\n")
        
        if corrupted_build > 0:
            out.write(f"WARNING: {corrupted_build} entries have wrong player's build order (streamer instead of opponent).\n")
            out.write("These were caused by a buggy load_learning_data.py script.\n")
            out.write("Consider regenerating from database or removing these entries.\n\n")
        
        if low_matches > 0:
            out.write(f"WARNING: {low_matches} comments have low self-match scores. Review needed.\n")
        else:
            out.write("SUCCESS: All valid comments have acceptable self-match scores.\n")
    
    # Print summary to console
    print()
    print("=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)
    print(f"Total comments: {len(comments)}")
    print(f"With build order: {len(comments) - no_build}")
    print()
    print(f"Self-match results:")
    print(f"  PERFECT (100%): {perfect_matches}")
    print(f"  HIGH (90-99%): {high_matches}")
    print(f"  MEDIUM (70-89%): {medium_matches}")
    print(f"  LOW (<70%): {low_matches}")
    print(f"  CORRUPTED (wrong player): {corrupted_build}")
    print()
    if corrupted_build > 0:
        print(f"WARNING: {corrupted_build} entries have wrong player's build order!")
    print(f"Report saved to: {output_file}")

if __name__ == "__main__":
    main()

