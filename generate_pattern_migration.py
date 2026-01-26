"""
Generate SQL migration file for pattern learning data
Reads JSON files and creates INSERT statements
"""
import json
import sys
from datetime import datetime

print("Loading JSON data...")

# Load patterns
with open('data/patterns.json', 'r', encoding='utf-8') as f:
    patterns = json.load(f)
print(f"Loaded {len(patterns)} patterns")

# Load comments
with open('data/comments.json', 'r', encoding='utf-8') as f:
    comments_data = json.load(f)
comments = comments_data.get('comments', [])
print(f"Loaded {len(comments)} comments")

# Load learning stats
with open('data/learning_stats.json', 'r', encoding='utf-8') as f:
    stats = json.load(f)
print(f"Loaded learning stats")

print("\nGenerating SQL file...")

with open('migrate_data_pattern_learning.sql', 'w', encoding='utf-8') as sql:
    # Header
    sql.write("-- Pattern Learning Data Migration\n")
    sql.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    sql.write(f"-- Patterns: {len(patterns)}, Comments: {len(comments)}\n\n")
    
    # Create tables
    sql.write("-- =====================================================\n")
    sql.write("-- CREATE TABLES\n")
    sql.write("-- =====================================================\n\n")
    
    # Patterns table
    sql.write("""
CREATE TABLE IF NOT EXISTS PatternLearning (
    pattern_id VARCHAR(50) PRIMARY KEY,
    signature JSON NOT NULL,
    label VARCHAR(255),
    opponent_race VARCHAR(20),
    player_race VARCHAR(20),
    game_count INT DEFAULT 1,
    similarity_threshold FLOAT DEFAULT 0.0,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_label (label),
    INDEX idx_races (opponent_race, player_race)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

""")
    
    # Comments table
    sql.write("""
CREATE TABLE IF NOT EXISTS PlayerComments (
    comment_id VARCHAR(50) PRIMARY KEY,
    raw_comment TEXT,
    cleaned_comment TEXT,
    keywords JSON,
    opponent_name VARCHAR(255),
    opponent_race VARCHAR(20),
    result VARCHAR(10),
    map_name VARCHAR(255),
    duration VARCHAR(20),
    date_played DATETIME,
    build_order JSON,
    pattern_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_opponent (opponent_name),
    INDEX idx_date (date_played),
    INDEX idx_pattern (pattern_id),
    FOREIGN KEY (pattern_id) REFERENCES PatternLearning(pattern_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

""")
    
    # Learning stats table
    sql.write("""
CREATE TABLE IF NOT EXISTS LearningStats (
    stat_id INT AUTO_INCREMENT PRIMARY KEY,
    stat_key VARCHAR(255) NOT NULL,
    stat_value TEXT,
    category VARCHAR(100),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_key (stat_key),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

""")
    
    sql.write("\n-- =====================================================\n")
    sql.write("-- INSERT PATTERN DATA\n")
    sql.write("-- =====================================================\n\n")
    
    # Insert patterns (batch inserts for performance)
    batch_size = 100
    pattern_count = 0
    
    for i in range(0, len(patterns), batch_size):
        batch = list(patterns.items())[i:i+batch_size]
        
        sql.write("INSERT INTO PatternLearning (pattern_id, signature, label, opponent_race, player_race, game_count, similarity_threshold, metadata) VALUES\n")
        
        values = []
        for pattern_id, pattern_data in batch:
            # Extract data
            signature = json.dumps(pattern_data.get('signature', {}), ensure_ascii=False).replace("'", "''")
            label = pattern_data.get('label', '').replace("'", "''")
            opp_race = pattern_data.get('opponent_race', '').replace("'", "''")
            player_race = pattern_data.get('player_race', '').replace("'", "''")
            game_count = pattern_data.get('game_count', 1)
            similarity = pattern_data.get('similarity_threshold', 0.0)
            metadata = json.dumps({
                'confidence': pattern_data.get('confidence', 0.0),
                'last_seen': pattern_data.get('last_seen', ''),
                'variations': pattern_data.get('variations', [])
            }, ensure_ascii=False).replace("'", "''")
            
            values.append(f"('{pattern_id}', '{signature}', '{label}', '{opp_race}', '{player_race}', {game_count}, {similarity}, '{metadata}')")
            pattern_count += 1
        
        sql.write(',\n'.join(values))
        sql.write(';\n\n')
        
        if (i + batch_size) % 1000 == 0:
            print(f"  Generated {i + batch_size}/{len(patterns)} patterns...")
    
    print(f"✓ Generated {pattern_count} pattern inserts")
    
    sql.write("\n-- =====================================================\n")
    sql.write("-- INSERT COMMENT DATA\n")
    sql.write("-- =====================================================\n\n")
    
    # Insert comments (batch inserts)
    comment_count = 0
    
    for i in range(0, len(comments), batch_size):
        batch = comments[i:i+batch_size]
        
        sql.write("INSERT INTO PlayerComments (comment_id, raw_comment, cleaned_comment, keywords, opponent_name, opponent_race, result, map_name, duration, date_played, build_order, pattern_id) VALUES\n")
        
        values = []
        for comment in batch:
            comment_id = comment.get('id', f"comment_{i}").replace("'", "''")
            raw = (comment.get('raw_comment', '') or '').replace("'", "''")
            cleaned = (comment.get('cleaned_comment', '') or '').replace("'", "''")
            keywords = json.dumps(comment.get('keywords', []), ensure_ascii=False).replace("'", "''")
            
            game_data = comment.get('game_data', {})
            opp_name = str(game_data.get('opponent_name', '') or '').replace("'", "''")
            opp_race = str(game_data.get('opponent_race', '') or '').replace("'", "''")
            result = str(game_data.get('result', '') or '').replace("'", "''")
            map_name = str(game_data.get('map', '') or '').replace("'", "''")
            duration = str(game_data.get('duration', '') or '').replace("'", "''")
            date_str = game_data.get('date', '')
            
            # Parse date
            try:
                if date_str:
                    date_played = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                else:
                    date_played = 'NULL'
            except:
                date_played = 'NULL'
            
            build_order = json.dumps(game_data.get('build_order', []), ensure_ascii=False).replace("'", "''")
            pattern_id = (comment.get('matched_pattern_id', '') or 'NULL').replace("'", "''")
            if pattern_id == 'NULL':
                pattern_id_val = 'NULL'
            else:
                pattern_id_val = f"'{pattern_id}'"
            
            if date_played == 'NULL':
                values.append(f"('{comment_id}', '{raw}', '{cleaned}', '{keywords}', '{opp_name}', '{opp_race}', '{result}', '{map_name}', '{duration}', NULL, '{build_order}', {pattern_id_val})")
            else:
                values.append(f"('{comment_id}', '{raw}', '{cleaned}', '{keywords}', '{opp_name}', '{opp_race}', '{result}', '{map_name}', '{duration}', '{date_played}', '{build_order}', {pattern_id_val})")
            comment_count += 1
        
        sql.write(',\n'.join(values))
        sql.write(';\n\n')
        
        if (i + batch_size) % 1000 == 0:
            print(f"  Generated {i + batch_size}/{len(comments)} comments...")
    
    print(f"✓ Generated {comment_count} comment inserts")
    
    sql.write("\n-- =====================================================\n")
    sql.write("-- INSERT LEARNING STATS\n")
    sql.write("-- =====================================================\n\n")
    
    # Insert learning stats
    sql.write("INSERT INTO LearningStats (stat_key, stat_value, category) VALUES\n")
    
    stat_values = []
    
    # Total counts
    stat_values.append(f"('total_keywords', '{stats.get('total_keywords', 0)}', 'summary')")
    stat_values.append(f"('total_patterns', '{stats.get('total_patterns', 0)}', 'summary')")
    
    # Keyword breakdown
    keyword_breakdown = stats.get('keyword_breakdown', {})
    for keyword, count in keyword_breakdown.items():
        keyword_safe = keyword.replace("'", "''")
        stat_values.append(f"('{keyword_safe}', '{count}', 'keyword_count')")
    
    # Pattern breakdown
    pattern_breakdown = stats.get('pattern_breakdown', {})
    for pattern, count in pattern_breakdown.items():
        pattern_safe = pattern.replace("'", "''")
        stat_values.append(f"('{pattern_safe}', '{count}', 'pattern_count')")
    
    sql.write(',\n'.join(stat_values))
    sql.write(';\n\n')
    
    print(f"✓ Generated {len(stat_values)} stat inserts")
    
    # Footer
    sql.write("\n-- =====================================================\n")
    sql.write("-- MIGRATION COMPLETE\n")
    sql.write("-- =====================================================\n")
    sql.write(f"-- Total Patterns: {pattern_count}\n")
    sql.write(f"-- Total Comments: {comment_count}\n")
    sql.write(f"-- Total Stats: {len(stat_values)}\n")

print(f"\n✓ SQL file generated: migrate_data_pattern_learning.sql")
print(f"\nTo apply:")
print(f"  mysql -u user -p mathison < migrate_data_pattern_learning.sql")

