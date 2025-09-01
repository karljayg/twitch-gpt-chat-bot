# JSON Schema Reference - SC2 Pattern Learning System

## Overview
This document provides detailed JSON schema definitions and real examples from the SC2 Pattern Learning System data files.

---

## 📁 File Structure

```
data/
├── comments.json           # Primary learning data (147KB+)
├── patterns.json          # Build order patterns (70KB+)  
├── learning_stats.json    # Statistics and metrics (4KB+)
├── comments.json.backup   # Automatic backup
└── learning_stats.json.backup
```

---

## 📋 comments.json Schema

### Root Structure
```json
{
  "comments": [CommentEntry],
  "keyword_index": {
    "keyword": ["comment_id1", "comment_id2"]
  }
}
```

### CommentEntry Schema
```typescript
interface CommentEntry {
  id: string;                    // "comment_001", "comment_002", etc.
  raw_comment: string;           // Original player input
  cleaned_comment: string;       // Processed version for analysis
  comment: string;              // Backward compatibility field
  keywords: string[];           // Extracted strategic terms
  game_data: GameData;          // Full game context
  timestamp: string;            // ISO datetime when created
  has_player_comment: boolean;  // true=expert, false=AI generated
}
```

### GameData Schema
```typescript
interface GameData {
  opponent_name: string;        // Full opponent name (fixed from truncation bug)
  opponent_race: string;        // "Protoss", "Terran", "Zerg", "Random"
  result: string;              // "Victory", "Defeat", "Tie" 
  map: string;                 // Map name
  duration: string;            // "15m 30s" format
  date: string;                // "2024-12-19 23:14:01" format
  build_order: BuildStep[];    // Sequence of build steps
}
```

### BuildStep Schema  
```typescript
interface BuildStep {
  supply: number;              // Supply count when unit/building made
  name: string;               // Unit/building name
  time: number;               // Seconds from game start
}
```

### Real Example
```json
{
  "id": "comment_001",
  "raw_comment": "This is the first comment. Hello world.",
  "cleaned_comment": "This is the first comment Hello world",
  "comment": "This is the first comment. Hello world.",
  "keywords": ["first", "comment", "hello", "world"],
  "game_data": {
    "opponent_name": "Solstice",
    "opponent_race": "Protoss", 
    "result": "Lose",
    "map": "Ley Lines",
    "duration": "16m 58s",
    "date": "2024-12-19 23:14:01",
    "build_order": [
      {"supply": 12, "name": "Probe", "time": 0},
      {"supply": 13, "name": "Probe", "time": 17},
      {"supply": 14, "name": "Pylon", "time": 25}
    ]
  },
  "timestamp": "2025-09-01T10:52:07.910560",
  "has_player_comment": true
}
```

---

## 🔍 patterns.json Schema

### Root Structure
```json
{
  "pattern_001": PatternEntry,
  "pattern_002": PatternEntry,
  // ... more patterns
}
```

### PatternEntry Schema
```typescript
interface PatternEntry {
  signature: PatternSignature;  // Build order fingerprint
  comment_id: string;          // Reference to source comment
  game_id: string;             // Unique game identifier
  keywords: string[];          // Associated strategic terms
  sample_count: number;        // How many times pattern seen
  last_seen: string;           // ISO timestamp of last occurrence
  strategy_type: string;       // AI-classified strategy name
  race: string;               // Player race for this pattern
  confidence: number;         // Reliability score (0.0-1.0)
}
```

### PatternSignature Schema
```typescript
interface PatternSignature {
  early_game: BuildStep[];        // First 20 supply worth
  key_timings: BuildStep[];       // Important buildings/upgrades  
  opening_sequence: BuildStep[];  // Critical first 10 steps
}
```

### Real Example
```json
{
  "pattern_001": {
    "signature": {
      "early_game": [
        {"unit": "Drone", "count": 1, "order": 1, "supply": 12, "time": 0},
        {"unit": "Overlord", "count": 1, "order": 2, "supply": 13, "time": 12},
        {"unit": "Drone", "count": 1, "order": 3, "supply": 13, "time": 16}
      ],
      "key_timings": {},
      "opening_sequence": [
        {"unit": "Drone", "count": 1, "order": 1, "supply": 12, "time": 0},
        {"unit": "Overlord", "count": 1, "order": 2, "supply": 13, "time": 12}
      ]
    },
    "comment_id": "comment_001", 
    "game_id": "game_001",
    "keywords": ["macro", "expand", "economy"],
    "sample_count": 1,
    "last_seen": "2025-09-01T10:52:07.910560",
    "strategy_type": "economic_opening",
    "race": "Zerg",
    "confidence": 0.8
  }
}
```

---

## 📊 learning_stats.json Schema

### Root Structure
```typescript
interface LearningStats {
  total_keywords: number;           // Count of unique strategic terms
  total_patterns: number;          // Count of unique build patterns
  keyword_breakdown: {             // Frequency of each keyword
    [keyword: string]: number;
  };
  pattern_breakdown?: {            // Optional pattern statistics
    [pattern_type: string]: number;
  };
  last_updated?: string;           // ISO timestamp of last update
}
```

### Real Example
```json
{
  "total_keywords": 221,
  "total_patterns": 150,
  "keyword_breakdown": {
    "first": 3,
    "rusher": 5, 
    "bio": 7,
    "into": 28,
    "muta": 6,
    "mech": 6,
    "all-in": 12,
    "proxy": 8,
    "cannon": 4,
    "rush": 9
  },
  "pattern_breakdown": {
    "economic_opening": 45,
    "aggressive_opening": 32,
    "tech_focused": 28,
    "all_in": 25,
    "defensive": 20
  },
  "last_updated": "2025-09-01T10:52:09.123456"
}
```

---

## 🔑 Keyword Index Schema

The keyword index provides fast lookup from strategic terms to relevant comments.

### Structure
```json
{
  "keyword_index": {
    "proxy": ["comment_015", "comment_032", "comment_078"],
    "cannon": ["comment_015", "comment_067"], 
    "rush": ["comment_004", "comment_015", "comment_023"],
    "bio": ["comment_011", "comment_043", "comment_089"],
    "mech": ["comment_021", "comment_055", "comment_092"]
  }
}
```

### Usage Pattern
```typescript
// Find all comments about "proxy" strategies
const proxyComments = commentData.comments.filter(
  comment => keyword_index["proxy"].includes(comment.id)
);

// Get strategic insights about proxies
const proxyInsights = proxyComments.map(comment => ({
  strategy: comment.comment,
  opponent: comment.game_data.opponent_name,
  success: comment.game_data.result === "Victory"
}));
```

---

## 🎯 Strategic Data Examples

### Opponent Intelligence
```json
{
  "opponent_name": "IIIIIIIIIIII", 
  "opponent_race": "Protoss",
  "historical_patterns": [
    "cannon rush into immortal contain",
    "proxy 4 gate all in", 
    "DT drop to disruptor timing"
  ],
  "success_rate_against": 0.65,
  "last_played": "2024-12-30 21:21:15"
}
```

### Build Order Pattern
```json
{
  "pattern_name": "protoss_oracle_opener",
  "signature": {
    "early_game": [
      {"supply": 14, "name": "Pylon", "time": 25},
      {"supply": 15, "name": "Gateway", "time": 43}, 
      {"supply": 19, "name": "CyberneticsCore", "time": 92},
      {"supply": 27, "name": "Stargate", "time": 155},
      {"supply": 29, "name": "Oracle", "time": 190}
    ]
  },
  "strategic_purpose": "Early harassment and scouting",
  "transitions": ["void ray tech", "phoenix range", "tempest late game"],
  "counters": ["early spores", "quick hydras", "muta response"]
}
```

### Keyword Analytics
```json
{
  "strategic_keywords": {
    "aggressive": ["proxy", "rush", "all-in", "cheese", "pressure"],
    "defensive": ["turtle", "contain", "defensive", "hold", "survive"],
    "economic": ["expand", "macro", "economy", "greedy", "fast"],
    "tech": ["upgrade", "tech", "transition", "late-game", "tier"],
    "units": ["marine", "stalker", "zergling", "oracle", "muta"],
    "buildings": ["barracks", "gateway", "spawning", "stargate", "robo"]
  },
  "sentiment_analysis": {
    "positive_outcomes": ["contain", "defend", "counter", "punish"],
    "negative_outcomes": ["rusher", "abuse", "cheese", "unfair"],
    "neutral_analysis": ["macro", "tech", "timing", "transition"]
  }
}
```

---

## 🔧 Data Validation Rules

### Required Fields
- `opponent_name`: Must be non-empty string (not single letters)
- `game_data.result`: Must be "Victory", "Defeat", or "Tie"
- `build_order`: Must have at least 1 step for pattern creation
- `keywords`: Must have at least 1 keyword for learning
- `timestamp`: Must be valid ISO datetime format

### Data Quality Checks
```typescript
function validateCommentEntry(entry: CommentEntry): boolean {
  return (
    entry.id.startsWith("comment_") &&
    entry.game_data.opponent_name.length > 1 &&
    entry.keywords.length > 0 &&
    entry.game_data.build_order.length > 0 &&
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(entry.timestamp)
  );
}
```

### Pattern Validation
```typescript
function validatePattern(pattern: PatternEntry): boolean {
  return (
    pattern.signature.early_game.length > 0 &&
    pattern.confidence >= 0.0 && pattern.confidence <= 1.0 &&
    pattern.sample_count > 0 &&
    pattern.keywords.length > 0
  );
}
```

---

## 🚀 Usage Examples

### Query Comments by Opponent
```typescript
const opponentComments = comments.filter(
  c => c.game_data.opponent_name === "IIIIIIIIIIII"
);
```

### Find Patterns by Strategy Type
```typescript
const aggressivePatterns = Object.values(patterns).filter(
  p => p.strategy_type === "aggressive_opening"
);
```

### Get Most Common Keywords
```typescript
const topKeywords = Object.entries(learning_stats.keyword_breakdown)
  .sort(([,a], [,b]) => b - a)
  .slice(0, 10);
```

### Strategic Intelligence Lookup
```typescript
function getOpponentIntelligence(opponentName: string) {
  const games = comments.filter(
    c => c.game_data.opponent_name === opponentName
  );
  
  return {
    total_games: games.length,
    win_rate: games.filter(g => g.game_data.result === "Victory").length / games.length,
    common_strategies: extractCommonKeywords(games),
    last_played: Math.max(...games.map(g => new Date(g.timestamp).getTime()))
  };
}
```

This JSON schema provides the complete data model for understanding, validating, and working with the SC2 Pattern Learning System data.
