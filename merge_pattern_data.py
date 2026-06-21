#!/usr/bin/env python3
"""
Merge pattern learning data from data1 and data2 folders into a single data folder.
This script will:
1. Check if data/data1 and data/data2 exist
2. Load all JSON files from both folders
3. Merge the data intelligently (deduplicate patterns and comments)
4. Save merged data to data/ folder
"""

import os
import json
from datetime import datetime
from collections import defaultdict

def load_json_file(filepath):
    """Load a JSON file, return None if it doesn't exist or is invalid"""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None

def save_json_file(filepath, data):
    """Save data to a JSON file"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)

def merge_patterns(patterns1, patterns2):
    """Merge two patterns dictionaries, deduplicating by signature"""
    merged = {}
    seen_signatures = {}
    pattern_id = 0
    
    # Process patterns from both sources
    for patterns_dict, source in [(patterns1, 'data1'), (patterns2, 'data2')]:
        if not patterns_dict:
            continue
            
        for pattern_name, pattern_data in patterns_dict.items():
            # Create signature hash for deduplication
            signature = pattern_data.get('signature', {})
            signature_str = json.dumps(signature, sort_keys=True)
            
            if signature_str not in seen_signatures:
                # New unique pattern
                pattern_id += 1
                new_pattern_name = f"pattern_{pattern_id:03d}"
                merged[new_pattern_name] = pattern_data.copy()
                seen_signatures[signature_str] = new_pattern_name
                print(f"  Added pattern from {source}: {pattern_name} -> {new_pattern_name}")
            else:
                # Duplicate pattern - merge keywords and increment sample count
                existing_name = seen_signatures[signature_str]
                existing_pattern = merged[existing_name]
                
                # Merge keywords (avoid duplicates)
                existing_keywords = set(existing_pattern.get('keywords', []))
                new_keywords = set(pattern_data.get('keywords', []))
                merged_keywords = list(existing_keywords | new_keywords)
                existing_pattern['keywords'] = merged_keywords
                
                # Increment sample count
                existing_pattern['sample_count'] = existing_pattern.get('sample_count', 1) + pattern_data.get('sample_count', 1)
                
                # Update last_seen to most recent
                existing_last_seen = existing_pattern.get('last_seen', '')
                new_last_seen = pattern_data.get('last_seen', '')
                if new_last_seen > existing_last_seen:
                    existing_pattern['last_seen'] = new_last_seen
                
                print(f"  Merged duplicate pattern from {source}: {pattern_name} -> {existing_name}")
    
    return merged

def merge_comments(comments1, comments2):
    """Merge two comments data structures, deduplicating by comment text and game data"""
    merged_comments = []
    merged_keyword_index = defaultdict(list)
    
    seen_comments = set()  # Track by (comment_text, game_id) tuple
    comment_id = 0
    
    # Process comments from both sources
    for comments_data, source in [(comments1, 'data1'), (comments2, 'data2')]:
        if not comments_data:
            continue
        
        comments_list = comments_data.get('comments', [])
        keyword_index = comments_data.get('keyword_index', {})
        
        for comment in comments_list:
            comment_text = comment.get('comment', '')
            game_data = comment.get('game_data', {})
            game_id = game_data.get('game_id', '') or game_data.get('opponent', '') + '_' + game_data.get('map', '')
            
            # Create unique identifier
            comment_key = (comment_text, game_id)
            
            if comment_key not in seen_comments:
                # New unique comment
                comment_id += 1
                new_comment_id = f"comment_{comment_id:03d}"
                
                new_comment = comment.copy()
                new_comment['id'] = new_comment_id
                merged_comments.append(new_comment)
                seen_comments.add(comment_key)
                
                # Add to keyword index
                for keyword in comment.get('keywords', []):
                    merged_keyword_index[keyword].append(new_comment_id)
                
                print(f"  Added comment from {source}: {new_comment_id}")
            else:
                print(f"  Skipped duplicate comment from {source}: {comment.get('id', 'unknown')}")
    
    return {
        "comments": merged_comments,
        "keyword_index": dict(merged_keyword_index)
    }

def merge_stats(stats1, stats2):
    """Merge learning statistics"""
    merged = {
        "total_keywords": 0,
        "keyword_breakdown": {},
        "total_patterns": 0,
        "total_comments": 0,
        "last_saved": datetime.now().isoformat(),
        "merged_from": ["data1", "data2"]
    }
    
    for stats in [stats1, stats2]:
        if not stats:
            continue
        
        merged["total_keywords"] = max(merged.get("total_keywords", 0), stats.get("total_keywords", 0))
        merged["total_patterns"] = max(merged.get("total_patterns", 0), stats.get("total_patterns", 0))
        merged["total_comments"] = max(merged.get("total_comments", 0), stats.get("total_comments", 0))
        
        # Merge keyword breakdown
        for keyword, count in stats.get("keyword_breakdown", {}).items():
            merged["keyword_breakdown"][keyword] = merged["keyword_breakdown"].get(keyword, 0) + count
    
    return merged

def main():
    print("=" * 60)
    print("Pattern Learning Data Merger")
    print("=" * 60)
    
    data_dir = "data"
    data1_dir = os.path.join(data_dir, "data1")
    data2_dir = os.path.join(data_dir, "data2")
    
    # Check if folders exist
    if not os.path.exists(data1_dir):
        print(f"ERROR: {data1_dir} does not exist!")
        return
    
    if not os.path.exists(data2_dir):
        print(f"ERROR: {data2_dir} does not exist!")
        return
    
    print(f"\nFound data1 folder: {data1_dir}")
    print(f"Found data2 folder: {data2_dir}")
    
    # Load files from data1
    print("\nLoading data from data1...")
    patterns1 = load_json_file(os.path.join(data1_dir, "patterns.json"))
    comments1 = load_json_file(os.path.join(data1_dir, "comments.json"))
    stats1 = load_json_file(os.path.join(data1_dir, "learning_stats.json"))
    
    # Load files from data2
    print("Loading data from data2...")
    patterns2 = load_json_file(os.path.join(data2_dir, "patterns.json"))
    comments2 = load_json_file(os.path.join(data2_dir, "comments.json"))
    stats2 = load_json_file(os.path.join(data2_dir, "learning_stats.json"))
    
    # Show what we found
    print("\nData Summary:")
    print(f"  data1 - Patterns: {len(patterns1) if patterns1 else 0}, Comments: {len(comments1.get('comments', [])) if comments1 else 0}")
    print(f"  data2 - Patterns: {len(patterns2) if patterns2 else 0}, Comments: {len(comments2.get('comments', [])) if comments2 else 0}")
    
    # Merge data
    print("\nMerging patterns...")
    merged_patterns = merge_patterns(patterns1 or {}, patterns2 or {})
    print(f"  Total unique patterns after merge: {len(merged_patterns)}")
    
    print("\nMerging comments...")
    merged_comments = merge_comments(comments1 or {}, comments2 or {})
    print(f"  Total unique comments after merge: {len(merged_comments['comments'])}")
    
    print("\nMerging statistics...")
    merged_stats = merge_stats(stats1 or {}, stats2 or {})
    merged_stats["total_patterns"] = len(merged_patterns)
    merged_stats["total_comments"] = len(merged_comments['comments'])
    
    # Backup existing data files if they exist
    print("\nBacking up existing data files...")
    for filename in ["patterns.json", "comments.json", "learning_stats.json"]:
        existing_file = os.path.join(data_dir, filename)
        if os.path.exists(existing_file):
            backup_file = os.path.join(data_dir, f"{filename}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            import shutil
            shutil.copy2(existing_file, backup_file)
            print(f"  Backed up {filename} to {os.path.basename(backup_file)}")
    
    # Save merged data
    print("\nSaving merged data...")
    save_json_file(os.path.join(data_dir, "patterns.json"), merged_patterns)
    print(f"  Saved {len(merged_patterns)} patterns to data/patterns.json")
    
    save_json_file(os.path.join(data_dir, "comments.json"), merged_comments)
    print(f"  Saved {len(merged_comments['comments'])} comments to data/comments.json")
    
    save_json_file(os.path.join(data_dir, "learning_stats.json"), merged_stats)
    print(f"  Saved statistics to data/learning_stats.json")
    
    print("\n" + "=" * 60)
    print("Merge completed successfully!")
    print("=" * 60)
    print(f"\nFinal counts:")
    print(f"  Patterns: {len(merged_patterns)}")
    print(f"  Comments: {len(merged_comments['comments'])}")
    print(f"  Keywords: {len(merged_comments['keyword_index'])}")

if __name__ == "__main__":
    main()
