# SC2 Pattern Learning System Documentation

## Overview

The SC2 Pattern Learning System is an intelligent build order analysis and pattern recognition system designed to learn from your StarCraft 2 expertise and provide strategic insights for repeat opponents. The system combines your expert player comments with AI analysis of replay data to create a comprehensive learning database that improves over time.

> **✅ BLIZZARD API FIXED**
> 
> The SC2 localhost JSON API now correctly returns `isReplay: false` for real games and `isReplay: true` for replay viewing. The system can now properly distinguish between real games and replay viewing.

## Complete System Flow

### 🎮 **Live Game Flow (Your Original System)**
```
Game Ends → You Type Comment in Terminal → Comment Saved to Database → Pattern Learning
```

**This is your existing system and it works perfectly!**

### 🤖 **Auto-Processing Flow (New Addition)**
```
Game Ends → No Comment Entered → AI Analyzes Replay → Creates AI Pattern → You Can Add Comment Later
```

**This is the new system that complements your existing system.**

### 📝 **Post-Game Comment Management (New Addition)**
```
Previously Processed Game → Use add_player_comment.py → Add Expert Insight → Upgrade AI Pattern
```

**This allows you to add expert insights to games that were auto-processed.**

## Data Model & Storage

### 🗄️ **Database Storage (Your Original System)**
- **Table**: `REPLAYS.Player_Comments`
- **Method**: `update_player_comments_in_last_replay()`
- **Purpose**: Stores your expert comments for database queries
- **Status**: ✅ **Unchanged and working perfectly**

### 📁 **File Storage (Pattern Learning System)**
```
data/
├── patterns.json          # Learned patterns with build signatures
├── comments.json          # Comment storage with dual format (raw + cleaned)
└── learning_stats.json    # System statistics and metadata
```

### 🔄 **Data Flow Architecture**
```
Game Data → Pattern Learning System → File Storage → ML Analysis → Strategic Insights
     ↓
Database Storage (Your Comments) → Database Queries → Historical Analysis
```

## How Everything Works Together

### 1. **During Live Games (Your Original System)**

#### Step 1: Game Ends
When a StarCraft 2 game ends, the system automatically:
- Extracts game data (opponent, race, result, map, duration, date)
- Analyzes replay data for build order information
- Prepares for player comment input

#### Step 2: Comment Prompt
The system displays a formatted game summary and prompts for input:
```
🎮 GAME COMPLETED - ENTER PLAYER COMMENT
============================================================
Opponent: PlayerX
Race: Zerg
Result: Victory
Map: Acropolis
Duration: 8m 32s
Date: 2024-01-15 14:30:00
============================================================
Enter player comment about the game (or press Enter to skip):
```

#### Step 3: Learning Process
- **With Comment**: System extracts keywords and creates expert patterns
- **Without Comment**: AI analyzes replay data and creates learned patterns
- **Pattern Storage**: All patterns are saved to persistent files
- **Keyword Association**: Comments are linked to relevant SC2 strategy terms

### 2. **Auto-Processing (New Addition)**

#### When You Don't Enter a Comment
If you press Enter without typing a comment:
1. **AI Analysis**: System analyzes the replay data automatically
2. **Pattern Creation**: Creates an AI-generated pattern with confidence score
3. **File Storage**: Saves the pattern to `data/patterns.json`
4. **Later Enhancement**: You can add your expert insight later using the management tools

#### AI Learning Process
```python
def process_game_without_comment(self, game_data):
    # Analyze first 60 supply for strategy indicators
    strategy_guess = self._guess_strategy_from_build(build_data)
    
    # Calculate AI confidence in the guess
    ai_confidence = self._calculate_ai_confidence(build_data)
    
    # Store as AI-learned pattern
    ai_comment_data = {
        'has_player_comment': False,  # AI-generated
        'ai_confidence': ai_confidence
    }
```

### 3. **Post-Game Comment Management (New Addition)**

#### Command-Line Interface
```bash
# List games that need expert comments
python add_player_comment.py list

# Add expert comment to a game
python add_player_comment.py add DKeyAbuser "Royal Blood LE" "2025-09-02 15:30" "This was a speedling all-in that I defended with cannons"

# Replace AI comment with expert insight
python add_player_comment.py edit DKeyAbuser "Royal Blood LE" "2025-09-02 15:30" "This was actually a roach rush, not speedling"
```

#### Comment Management Features
- **List Games**: Shows games that only have AI-generated patterns
- **Add Comments**: Add expert insights to previously processed games
- **Edit Comments**: Replace AI comments with your expert insights
- **Upgrade Patterns**: Convert AI patterns to expert patterns

### 4. **ML Analysis Integration**

#### Pattern Matching
The ML analysis system uses both:
- **Expert Patterns**: From your player comments (higher priority)
- **AI Patterns**: From automatic analysis (lower priority)

#### Priority System
```python
# Expert insights get priority boost
if pattern.get('has_player_comment', False):
    priority_boost = 1.0  # Expert insight
else:
    priority_boost = 0.0  # AI-generated
```

## Key Features

### 🧠 Dual Learning Approach
- **Expert Learning**: Extracts strategic insights from your player comments
- **AI Learning**: Analyzes replay data when no player comment is provided
- **Pattern Recognition**: Identifies build order similarities and strategic patterns
- **Opponent Intelligence**: Provides insights for repeat opponents based on learned patterns

### 💾 Persistent Storage
- **File-based persistence** using JSON files in `data/` directory
- **Survives bot restarts** - learning accumulates over time
- **Automatic backup** after every learning operation
- **Easy data inspection** and manual editing capabilities

### 🎯 Strategic Focus
- **First 60 supply analysis** (configurable via `BUILD_ORDER_COUNT_TO_ANALYZE`)
- **Early game focus** where strategic decisions are made
- **Key building timings** for critical structures
- **Opening sequence analysis** for pattern recognition

### 🚫 Duplicate Prevention
- **Smart game identification** prevents re-learning from the same replay
- **Unique game signatures** based on opponent, map, duration, and date
- **Automatic duplicate detection** when watching replays
- **Efficient learning** without redundant prompts or data

### 🏗️ **Improved Build Order Structure**
- **Consolidated Units**: Consecutive identical units are grouped with counts and order
- **Efficient Storage**: `{"unit": "Probe", "count": 3, "order": 1}` instead of `["Probe", "Probe", "Probe"]`
- **Better ML Preparation**: Structured data format optimized for machine learning analysis
- **Order Preservation**: Maintains strategic sequence information for pattern recognition

### 📝 **Dual Comment Storage**
- **Raw Comments**: Original human input preserved exactly as entered
- **Cleaned Comments**: Processed version for analysis (punctuation removed, normalized)
- **Authenticity**: Preserves authentic human input while enabling clean ML analysis
- **Backward Compatibility**: Maintains existing comment structure

### 🔍 **Enhanced Keyword Extraction**
- **Smart Cleaning**: Removes punctuation (except hyphens), normalizes whitespace
- **Deduplication**: Eliminates duplicate keywords within the same comment
- **Strategic Filtering**: Maintains meaningful SC2 terms while removing noise
- **ML Optimization**: Cleaner data for better machine learning performance

### 🧹 **Data Quality & Maintenance**
- **Automatic Backup**: Creates backup files before major changes
- **Duplicate Prevention**: Built-in safeguards against data corruption
- **Data Validation**: Ensures consistency across all files
- **Cleanup Tools**: Scripts available for data maintenance

## System Architecture

### Core Components

#### 1. SC2PatternLearner Class
```python
class SC2PatternLearner:
    def __init__(self, db, logger):
        self.patterns = defaultdict(list)           # Pattern storage
        self.comment_keywords = defaultdict(set)    # Keyword associations
        self.all_patterns = []                      # Centralized pattern list
        self.db = db                               # Database connection
        self.logger = logger                       # Logging system
```

#### 2. Data Storage Structure
```
data/
├── patterns.json          # Learned patterns with build signatures
├── comments.json          # Comment storage with dual format (raw + cleaned)
└── learning_stats.json    # System statistics and metadata
```

#### 3. Pattern Signature Format
```python
signature = {
    'early_game': [        # First 60 supply buildings/units (consolidated)
        {
            'unit': 'Probe',      # Unit/building name
            'count': 3,           # Number of consecutive units
            'order': 1,           # Strategic order in build sequence
            'supply': 13,         # Supply count when built
            'time': 120           # Game time in seconds
        }
    ],
    'key_timings': {},     # Critical building timings
    'opening_sequence': [] # First 10 buildings in order (consolidated)
}
```

#### 4. Complete Pattern Entry Format
```python
pattern_entry = {
    'signature': pattern_signature,           # Build order signature
    'comment': 'Expert insight or AI comment', # Human or AI comment
    'keywords': ['strategy', 'terms'],        # Extracted keywords
    'game_data': {                           # Complete game information
        'opponent_name': 'PlayerX',
        'opponent_race': 'zerg',
        'map': 'Acropolis',
        'duration': '8m 32s',
        'date': '2024-01-15 14:30:00',
        'result': 'Victory',
        'build_order': [...]                 # Full build order data
    },
    'has_player_comment': True,              # Expert insight vs AI
    'ai_confidence': 0.8,                    # AI confidence (if applicable)
    'timestamp': '2024-01-15T14:30:00'      # When pattern was created
}
```

## Game Detection System

The system now properly distinguishes between real games and replay viewing using the `isReplay` flag from the SC2 localhost JSON API:

- **Real games** (you playing) → `isReplay: false` → Triggers pattern learning
- **Replay viewing** (you watching) → `isReplay: true` → Does NOT trigger pattern learning

This ensures that pattern learning only occurs when you're actually playing, not when watching replays.

---

## How It Works

### 1. Game Completion Flow

#### Step 1: Game Ends
When a StarCraft 2 game ends, the system automatically:
- Extracts game data (opponent, race, result, map, duration, date)
- Analyzes replay data for build order information
- Prepares for player comment input

#### Step 2: Comment Prompt
The system displays a formatted game summary and prompts for input:
```
🎮 GAME COMPLETED - ENTER PLAYER COMMENT
============================================================
Opponent: PlayerX
Race: Zerg
Result: Victory
Map: Acropolis
Duration: 8m 32s
Date: 2024-01-15 14:30:00
============================================================
Enter player comment about the game (or press Enter to skip):
```

#### Step 3: Learning Process
- **With Comment**: System extracts keywords and creates expert patterns
- **Without Comment**: AI analyzes replay data and creates learned patterns
- **Pattern Storage**: All patterns are saved to persistent files
- **Keyword Association**: Comments are linked to relevant SC2 strategy terms

#### Step 4: Duplicate Detection
- **Game ID Generation**: Creates unique identifier from opponent + map + duration + date
- **Duplicate Check**: Verifies if game has already been processed
- **Smart Skipping**: Prevents re-learning from replay viewing or duplicate games
- **Efficient Learning**: Only processes new, unique games

### 2. Pattern Learning Process

#### Expert Comment Processing
```python
def _process_new_comment(self, game_data, comment):
    # Extract SC2 strategy keywords
    keywords = self._extract_keywords(comment)
    
    # Create pattern signature from build data
    pattern_signature = self._create_pattern_signature(build_data)
    
    # Store with expert insight marker
    comment_data = {
        'has_player_comment': True,  # Expert insight
        'ai_confidence': None        # Not AI-generated
    }
```

#### AI Learning Process
```python
def process_game_without_comment(self, game_data):
    # Analyze first 60 supply for strategy indicators
    strategy_guess = self._guess_strategy_from_build(build_data)
    
    # Calculate AI confidence in the guess
    ai_confidence = self._calculate_ai_confidence(build_data)
    
    # Store as AI-learned pattern
    ai_comment_data = {
        'has_player_comment': False,  # AI-generated
        'ai_confidence': ai_confidence
    }
```

### 3. Duplicate Detection System

#### Game Identification
```python
def _generate_game_id(self, game_data):
    # Create unique ID from: opponent + map + duration + date
    opponent = game_data.get('opponent_name', 'Unknown')
    map_name = game_data.get('map', 'Unknown')
    duration = game_data.get('duration', 'Unknown')
    date_part = game_data.get('date', '').split(' ')[0]  # YYYY-MM-DD only
    
    game_id = f"{opponent}_{map_name}_{duration}_{date_part}"
    return game_id.lower().replace(' ', '_').replace(':', '_')
```

#### Duplicate Prevention
```python
def _is_game_already_processed(self, game_id):
    # Check existing patterns and comments for this game ID
    # Prevents duplicate prompts when watching replays
    # Returns True if game already processed, False if new
```

**Benefits:**
- 🚫 **No duplicate prompts** when watching replays
- 🎯 **Real games still trigger** pattern learning
- 💾 **Efficient storage** without redundant data
- 🔄 **Works with Blizzard's broken API**

### 4. Pattern Recognition

#### Build Order Analysis
The system focuses on the first 60 supply (configurable) because:
- **Strategic decisions** are made in early game
- **Build order patterns** are most consistent early
- **Late game** is too variable and chaotic
- **Timing windows** are critical for strategy identification

#### Key Building Detection
The system tracks critical buildings for each race:
```python
# Zerg Key Buildings
'SpawningPool', 'RoachWarren', 'BanelingNest', 'Spire', 'NydusNetwork'

# Terran Key Buildings  
'Barracks', 'Factory', 'Starport', 'FusionCore', 'Armory', 'NuclearFacility'

# Protoss Key Buildings
'Gateway', 'Forge', 'TwilightCouncil', 'RoboticsFacility', 'Stargate'
```

#### Similarity Calculation
```python
def _calculate_similarity(self, current, known):
    score = 0.0
    
    # Early game similarity (40% weight)
    early_match = len(set(current['early_game']) & set(known['early_game']))
    early_total = len(set(current['early_game']) | set(known['early_game']))
    score += (early_match / early_total) * 0.4
    
    # Building sequence similarity (30% weight)
    seq_match = len(set(current['opening_sequence']) & set(known['opening_sequence']))
    seq_total = len(set(current['opening_sequence']) | set(known['opening_sequence']))
    score += (seq_match / seq_total) * 0.3
    
    # Timing similarity (30% weight)
    # Compares building timings within 30 seconds
    score += timing_similarity * 0.3
    
    return score
```

### 5. Insight Generation

#### For Repeat Opponents
When facing a previous opponent, the system provides:

**Expert Insights** (from your comments):
```
🎯 PlayerX tends to do Roach rush - you noted this before
```

**AI Insights** (from learned patterns):
```
🤖 I think based on previous games vs. PlayerX, they tend to do Early zerg aggression (confidence: 70%)
```

#### Insight Types
```python
insight = {
    'type': 'expert_insight' | 'ai_insight',
    'message': 'Formatted insight message',
    'confidence': 'high' | '70%' | '85%',
    'source': 'player_comment' | 'ai_learning',
    'strategy': 'Identified strategy type'
}
```

## Configuration

### Settings in `config.py`
```python
# Pattern Learning System Settings
ENABLE_PATTERN_LEARNING = True                    # Enable/disable system
PATTERN_LEARNING_SIMILARITY_THRESHOLD = 0.7      # Minimum similarity for pattern matching
PATTERN_LEARNING_MAX_PATTERNS = 1000             # Maximum patterns per keyword
PATTERN_DATA_DIR = "data"                        # Directory for pattern storage
BUILD_ORDER_COUNT_TO_ANALYZE = 60               # Supply threshold for analysis
```

### Adjustable Parameters
- **Similarity Threshold**: Higher = more strict pattern matching
- **Max Patterns**: Prevents memory bloat from excessive patterns
- **Supply Threshold**: How much of the game to analyze (60 supply recommended)

## Usage Instructions

### 1. System Integration
The pattern learning system is automatically integrated into your Twitch bot:
```python
# In api/twitch_bot.py
if config.ENABLE_PATTERN_LEARNING:
    self.pattern_learner = SC2PatternLearner(self.db, logger)

# In api/sc2_game_utils.py (delayed trigger)
if hasattr(self, 'pattern_learner'):
    # 15-second delay to allow replay processing
    timer_thread = threading.Thread(target=delayed_pattern_learning, daemon=True)
    timer_thread.start()
```

### 2. Adding Player Comments (Your Original System)
After each game:
1. **Review the game summary** displayed by the system
2. **Enter your strategic insights** using SC2 terminology
3. **Press Enter to skip** if no comment is desired
4. **System automatically learns** from your input

### 3. Comment Best Practices
**Good Examples:**
- "This player always goes roach rush - very predictable"
- "Fast expand into muta tech, standard macro play"
- "Early pool aggression, then transitions to macro"
- "Factory first, reaper harass into mech"

**Keywords the System Recognizes:**
- **Strategy**: rush, macro, tech, timing, all-in, cheese
- **Units**: zergling, roach, marine, zealot, stalker
- **Buildings**: pool, barracks, gateway, forge, factory
- **Playstyle**: aggressive, defensive, economic, fast, slow

### 4. Post-Game Comment Management (New System)
```bash
# List games that need expert comments
python add_player_comment.py list

# Add expert comment to a game
python add_player_comment.py add DKeyAbuser "Royal Blood LE" "2025-09-02 15:30" "This was a speedling all-in that I defended with cannons"

# Replace AI comment with expert insight
python add_player_comment.py edit DKeyAbuser "Royal Blood LE" "2025-09-02 15:30" "This was actually a roach rush, not speedling"
```

### 5. Viewing Learned Patterns
Check the `data/` directory for:
- **`patterns.json`**: All learned patterns with build signatures (updated format)
- **`comments.json`**: Comment storage with dual format (raw + cleaned)
- **`learning_stats.json`**: System statistics and metadata

## Test-Driven Development

### 🧪 **Development Philosophy**
The pattern learning system was developed using **Test-Driven Development (TDD)** to ensure:
- **Code Quality**: All features are thoroughly tested before implementation
- **Reliability**: Changes can be made confidently with comprehensive test coverage
- **Maintainability**: Easy to modify and extend without breaking existing functionality
- **Documentation**: Tests serve as living documentation of intended behavior

### 📋 **Test Suite Coverage**
The `test_pattern_learning_improvements.py` file contains **6 comprehensive tests**:

#### 1. **Build Order Structure Test**
```python
def test_improved_build_order_structure(self):
    """Test that build orders are stored with count and order information"""
    # Verifies consolidated unit format with counts and order
    # Ensures proper probe grouping and sequence preservation
```

#### 2. **Dual Comment Storage Test**
```python
def test_dual_comment_storage(self):
    """Test that both raw and cleaned comments are stored"""
    # Verifies raw_comment and cleaned_comment fields exist
    # Ensures backward compatibility with existing comment structure
```

#### 3. **Keyword Extraction Test**
```python
def test_improved_keyword_extraction(self):
    """Test that keywords are properly extracted without punctuation or duplicates"""
    # Verifies punctuation removal and keyword deduplication
    # Ensures clean data for machine learning
```

#### 4. **Build Order Consolidation Test**
```python
def test_build_order_consolidation(self):
    """Test that consecutive identical units are consolidated with counts"""
    # Verifies unit consolidation logic
    # Ensures proper pattern creation and numbering
```

#### 5. **Keyword Indexing Test**
```python
def test_keyword_indexing(self):
    """Test that keywords are properly indexed for fast lookup"""
    # Verifies efficient keyword-to-comment mapping
    # Ensures fast pattern retrieval
```

#### 6. **Data Consistency Test**
```python
def test_data_consistency(self):
    """Test that all data files are consistent with each other"""
    # Verifies cross-file data integrity
    # Ensures patterns, comments, and stats remain synchronized
```

### 🔄 **TDD Workflow**
1. **Write Test First**: Define expected behavior in test form
2. **Run Test**: Verify it fails (red phase)
3. **Implement Feature**: Write minimal code to pass test
4. **Run Test**: Verify it passes (green phase)
5. **Refactor**: Clean up code while maintaining test coverage
6. **Repeat**: Continue with next feature

### 🎯 **Benefits of TDD Approach**
- **Confidence**: Can modify code knowing tests will catch regressions
- **Design**: Tests force better API design and separation of concerns
- **Documentation**: Tests serve as executable specifications
- **Quality**: Catches bugs early in development cycle
- **Maintainability**: Easy to add new features without breaking existing ones

## Technical Details

### File Structure
```
documentation/
└── SC2_PATTERN_LEARNING_SYSTEM.md    # This file

data/
├── patterns.json                      # Pattern storage (updated format)
├── comments.json                      # Comment storage (dual format)
└── learning_stats.json                # System statistics

api/
├── pattern_learning.py                # Core learning system (improved)
├── sc2_game_utils.py                 # Game completion handling
└── twitch_bot.py                      # Bot integration

test/
└── test_pattern_learning_improvements.py  # Comprehensive test suite
```

### Data Persistence
- **JSON Format**: Human-readable and editable
- **Auto-save**: After every learning operation
- **Auto-load**: On system startup
- **Error Handling**: Graceful fallback if files are corrupted

### Performance Considerations
- **Memory Usage**: Patterns stored in memory during runtime
- **File I/O**: Minimal impact, only on save/load operations
- **Pattern Matching**: O(n) complexity for similarity calculations
- **Scalability**: Designed to handle thousands of patterns efficiently

## Troubleshooting

### Common Issues

#### 1. System Not Prompting for Comments
**Check:**
- `ENABLE_PATTERN_LEARNING = True` in config
- Pattern learner properly initialized in TwitchBot
- Game ended handler integration
- Game is a 1v1 (not 2v2 or team game)
- `isReplay` flag is correctly set to `false`

#### 2. Patterns Not Saving
**Check:**
- `data/` directory exists and is writable
- File permissions on the data directory
- Disk space availability

#### 3. Low Quality Insights
**Solutions:**
- Provide more detailed player comments
- Lower similarity threshold for more matches
- Increase supply threshold for more data

#### 4. System Performance Issues
**Optimizations:**
- Reduce `PATTERN_LEARNING_MAX_PATTERNS`
- Increase similarity threshold for fewer matches
- Clean up old patterns manually if needed

#### 5. Duplicate Prompts When Watching Replays
**This should not happen** with the fixed API. The system will:
- Correctly detect replay viewing as `isReplay: true`
- Return `REPLAY_ENDED` status
- NOT trigger pattern learning
- Log: "Detected REPLAY_ENDED (isReplay = true)"

### Debug Information
The system logs detailed information:
```
INFO: Pattern learning system initialized with 15 patterns
INFO: Scheduled delayed pattern learning trigger (15 seconds)
INFO: Replay data available - triggering pattern learning system
INFO: Game already processed (ID: opponent_map_duration_date), skipping comment prompt
INFO: AI learned pattern: Early zerg aggression (confidence: 70%)
INFO: Patterns saved to data/
```

## Future Enhancements

### Planned Features
1. **Machine Learning Integration**: True ML algorithms for pattern recognition
2. **Advanced Analytics**: Win rate correlation with build patterns
3. **Meta Analysis**: Strategy popularity and effectiveness tracking
4. **Visual Interface**: Web-based pattern visualization
5. **API Integration**: External tools for pattern analysis

### Extensibility
The system is designed for easy extension:
- **New keyword types** can be added to `_extract_keywords()`
- **Additional similarity metrics** can be implemented
- **Custom pattern formats** can be created
- **External data sources** can be integrated

## Best Practices

### For Optimal Learning
1. **Be Consistent**: Use similar terminology across comments
2. **Be Specific**: Include race, timing, and strategy details
3. **Regular Input**: Provide comments for most games
4. **Quality Over Quantity**: Better to have fewer, detailed comments than many vague ones

### For System Maintenance
1. **Monitor File Sizes**: Check `data/` directory growth
2. **Review Patterns**: Periodically examine learned patterns
3. **Clean Up**: Remove outdated or incorrect patterns if needed
4. **Backup**: Keep copies of pattern files for safety
5. **Data Quality**: Monitor for duplicate keywords or corrupted data
6. **Regular Testing**: Run test suite to ensure system integrity

### 🧹 **Recent Data Quality Improvements**
The system now includes automatic data quality safeguards:

- **Duplicate Detection**: Automatically identifies and prevents duplicate keywords
- **Backup Creation**: Creates `.backup` files before major changes
- **Data Validation**: Ensures consistency between patterns, comments, and stats
- **Cleanup Scripts**: Tools available for data maintenance and repair

**Example Backup Files:**
```
data/
├── comments.json          # Current data
├── comments.json.backup   # Backup before cleanup
├── learning_stats.json    # Current stats
└── learning_stats.json.backup  # Backup before cleanup
```

## Conclusion

The SC2 Pattern Learning System represents a significant advancement in automated StarCraft 2 analysis. By combining your expert insights with AI pattern recognition, it creates a powerful tool for understanding opponent tendencies and improving strategic decision-making.

The system is designed to be:
- **Intelligent**: Learns from your expertise
- **Persistent**: Maintains knowledge across sessions
- **Configurable**: Adapts to your preferences
- **Extensible**: Ready for future enhancements
- **Robust**: Properly distinguishes real games from replays
- **Efficient**: Prevents duplicate learning and redundant prompts

As you use the system, it will become increasingly valuable, providing deeper insights into opponent patterns and helping you develop more effective counter-strategies.

---

**Last Updated**: September 2025  
**Version**: 2.2 (Complete Player Comment Management System)  
**Author**: AI Assistant  
**System**: SC2 Pattern Learning System