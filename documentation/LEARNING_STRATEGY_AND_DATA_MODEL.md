# SC2 Pattern Learning: Strategy and Data Model

## Table of Contents
1. [Learning Strategy Overview](#learning-strategy-overview)
2. [Data Collection Decisions](#data-collection-decisions)
3. [Data Organization](#data-organization)
4. [Data Model Specifications](#data-model-specifications)
5. [JSON Schema Reference](#json-schema-reference)
6. [Strategic Reasoning](#strategic-reasoning)

---

## Learning Strategy Overview

### Core Philosophy
The SC2 Pattern Learning System operates on the principle that **expert human insight combined with automated pattern recognition** creates the most effective strategic analysis. Rather than relying solely on statistical analysis, the system prioritizes:

1. **Human Strategic Knowledge** - Player comments contain meta-strategic insights
2. **Context-Aware Learning** - Game context (opponent, map, result) influences pattern value
3. **Progressive Intelligence** - System learns and improves recognition over time
4. **Actionable Insights** - Focus on patterns that inform future decision-making

### Dual Learning Approach

#### 1. Expert Learning (Primary)
- **Source**: Player-provided comments after games
- **Value**: High - contains strategic reasoning and meta-knowledge
- **Processing**: Keyword extraction + pattern association
- **Output**: Strategic insights linked to build order patterns

#### 2. AI Learning (Secondary)
- **Source**: Replay analysis when no player comment provided
- **Value**: Medium - automated pattern recognition
- **Processing**: Build order analysis + strategy classification
- **Output**: AI-detected patterns with confidence ratings

### Learning Triggers
1. **Game End Event** → Data extraction from replay
2. **Comment Input** → Expert learning activation
3. **No Comment** → AI learning fallback
4. **Pattern Recognition** → Continuous background analysis

---

## Data Collection Decisions

### What We Collect

#### ✅ Essential Game Data
- **Opponent Information**: Full name, race, game result
- **Game Context**: Map, duration, date/time
- **Build Orders**: First 60 supply worth of units/buildings
- **Strategic Comments**: Player insights about the game

#### ✅ Learning Metadata  
- **Comment Keywords**: Extracted strategic terms
- **Pattern Signatures**: Build order fingerprints
- **Game Identifiers**: Prevent duplicate learning
- **Confidence Scores**: AI learning reliability

### What We Don't Collect

#### ❌ Excluded Data
- **Personal Information**: Beyond game usernames
- **Complete Replays**: Only strategic summaries
- **Opponent Strategies**: Analyze opponent build patterns and strategic tendencies
- **Micro-management**: Unit control details

### Collection Rationale

#### Why Build Orders?
- **Early Game Impact**: First 60 supply determines strategic direction
- **Reproducible Patterns**: Can be learned and applied
- **Decision Points**: Critical strategic moments
- **Pattern Recognition**: Similar openings often lead to similar strategies

#### Why Player Comments?
- **Strategic Context**: Explains why certain builds were chosen
- **Meta-Knowledge**: Information not visible in replay data
- **Learning Efficiency**: Faster than pure statistical analysis
- **Human Intuition**: Captures strategic nuances AI might miss

---

## Data Organization

### File Structure
```
data/
├── comments.json           # Primary learning data
├── patterns.json          # Build order pattern library
├── learning_stats.json    # Keyword and pattern statistics
├── comments.json.backup   # Automatic backup
└── learning_stats.json.backup
```

### Storage Strategy

#### 1. Centralized Comments (`comments.json`)
- **All learning data** in one efficient structure
- **Dual indexing**: By comment ID and by keyword
- **Rich metadata**: Full game context with each comment
- **Easy querying**: Both human and programmatic access

#### 2. Pattern Library (`patterns.json`)
- **Unique patterns only**: No duplicate build signatures
- **Reference system**: Keywords point to patterns
- **Confidence tracking**: AI vs expert pattern sources
- **Strategy classification**: Automated pattern categorization

#### 3. Statistics Tracking (`learning_stats.json`)
- **Keyword frequency**: Most common strategic terms
- **Pattern usage**: Build order popularity
- **Learning metrics**: System effectiveness tracking

### Indexing Strategy

#### Keyword Index
- **Purpose**: Fast lookup of comments by strategic terms
- **Structure**: `{"keyword": ["comment_001", "comment_002"]}`
- **Benefits**: Rapid pattern matching and strategy recall

#### Pattern Signatures
- **Purpose**: Identify duplicate or similar build orders
- **Structure**: Hash-based fingerprints of build sequences
- **Benefits**: Avoid redundant pattern storage

---

## Data Model Specifications

### Core Data Types

#### 1. Game Data Object
```typescript
interface GameData {
  opponent_name: string;     // Full opponent name (fixed from single letters)
  opponent_race: string;     // Protoss, Terran, Zerg, Random
  result: string;           // Victory, Defeat, Tie
  map: string;              // Map name
  duration: string;         // "15m 30s" format
  date: string;             // ISO datetime string
  build_order: BuildStep[]; // Ordered sequence of build steps
}
```

#### 2. Build Step Object
```typescript
interface BuildStep {
  supply: number;           // Supply count when unit/building was made
  name: string;            // Unit/building name (e.g., "Probe", "Gateway")
  time: number;            // Time in seconds from game start
}
```

#### 3. Comment Entry Object
```typescript
interface CommentEntry {
  id: string;                    // "comment_001"
  raw_comment: string;           // Original comment as entered
  cleaned_comment: string;       // Processed for analysis
  comment: string;              // Backward compatibility
  keywords: string[];           // Extracted strategic terms
  game_data: GameData;          // Associated game context
  timestamp: string;            // When comment was created
  has_player_comment: boolean;  // true for expert, false for AI
}
```

#### 4. Pattern Object
```typescript
interface Pattern {
  signature: {
    early_game: BuildStep[];        // First 20 supply
    key_timings: BuildStep[];       // Important buildings/units
    opening_sequence: BuildStep[];  // Critical early decisions
  };
  comment_id: string;              // Reference to source comment
  keywords: string[];              // All associated keywords
  sample_count: number;            // How many times seen
  strategy_type: string;           // AI classification
  race: string;                    // Player race for this pattern
  confidence: number;              // Reliability score (0-1)
}
```

### Data Relationships

#### Comment → Keywords → Patterns
1. **Comment Entry** contains keywords and game data
2. **Keywords** index back to relevant comments
3. **Patterns** are created from build orders in comments
4. **Keywords** reference patterns for strategic lookup

#### Pattern Signature Creation
```typescript
// Simplified signature creation logic
function createPatternSignature(buildOrder: BuildStep[]): PatternSignature {
  return {
    early_game: buildOrder.filter(step => step.supply <= 20),
    key_timings: buildOrder.filter(step => isKeyBuilding(step.name)),
    opening_sequence: buildOrder.slice(0, 10) // First 10 steps
  };
}
```

---

## Strategic Reasoning

### Why This Data Model?

#### 1. Efficiency Through Structure
- **Single source of truth**: Comments contain all necessary data
- **Minimal duplication**: Patterns reference comments, not duplicate data
- **Fast queries**: Keyword indexing enables rapid strategic lookup

#### 2. Human-Centric Design
- **Expert knowledge priority**: Player comments drive learning
- **Readable format**: JSON allows manual inspection and editing
- **Strategic focus**: Data model mirrors strategic thinking

#### 3. Scalability Considerations
- **Incremental learning**: New data doesn't require rebuilding
- **Memory efficiency**: Only active patterns kept in memory
- **File-based storage**: No database dependency for simple deployment

### Learning Optimization

#### Pattern Recognition Strategy
1. **Signature Matching**: Compare build order fingerprints
2. **Keyword Association**: Link strategic terms to patterns
3. **Context Weighting**: Recent games and successful patterns prioritized
4. **Opponent Intelligence**: Track patterns per opponent over time

#### Strategic Value Calculation
```typescript
function calculateStrategicValue(pattern: Pattern): number {
  const factors = {
    expertSource: pattern.confidence > 0.8 ? 2.0 : 1.0,
    recentness: getRecencyMultiplier(pattern.lastSeen),
    success: getSuccessRate(pattern.associatedGames),
    frequency: Math.log(pattern.sampleCount + 1)
  };
  
  return factors.expertSource * factors.recentness * 
         factors.success * factors.frequency;
}
```

### Data Quality Assurance

#### Validation Rules
- **Opponent names**: Must be full names (no single letters)
- **Build orders**: Minimum 5 steps for pattern creation
- **Keywords**: Minimum 2 characters, strategic relevance
- **Timestamps**: Valid ISO format for chronological ordering

#### Error Handling
- **Missing data**: Graceful degradation with partial patterns
- **Corrupt entries**: Automatic backup and recovery
- **Duplicate detection**: Hash-based signature comparison
- **Data migration**: Version compatibility for data structure changes

---

## Future Enhancements

### Planned Improvements
1. **Advanced Pattern Matching**: Fuzzy matching for similar build orders
2. **Opponent Profiling**: Individual strategy tracking per opponent
3. **Meta-Game Awareness**: Patch and balance update considerations
4. **Strategic Recommendations**: Proactive build order suggestions
5. **Performance Analytics**: Win rate correlation with learned patterns

### Data Model Evolution
- **Backward compatibility**: JSON structure allows gradual enhancement
- **Migration support**: Automated data structure updates
- **Extension points**: Additional metadata fields for future features
- **API stability**: Core data types remain consistent across versions

