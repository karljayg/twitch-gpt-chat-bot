# SC2 Pattern Learning System - Quick Reference

## 🚨 Important: Blizzard API Bug

**The SC2 localhost JSON API is broken** - `isReplay` always returns `true` even for real games.

**Our Workaround**: System detects real games by checking if streamer is playing, not by the broken `isReplay` flag.

**Current Behavior**: 
- ✅ Real games → Pattern learning works
- ⚠️ Watching replays → Also detected as "real game" (false positive)
- 🔧 Duplicate detection → Prevents re-learning from replays

## Quick Setup

### 1. Enable in Config
```python
# settings/config.py
ENABLE_PATTERN_LEARNING = True
PATTERN_DATA_DIR = "data"
BUILD_ORDER_COUNT_TO_ANALYZE = 60
```

### 2. System Integration
```python
# api/twitch_bot.py - Automatically initializes
# api/sc2_game_utils.py - 15-second delayed trigger
```

### 3. Data Directory
```
data/
├── patterns.json          # Learned patterns
├── keywords.json          # Keyword associations  
└── learning_stats.json    # System statistics
```

## How It Works

### Game Flow
1. **Game Ends** → `MATCH_ENDED` detected (streamer playing)
2. **15-second delay** → Replay processing completes
3. **Duplicate check** → Prevents re-learning from same game
4. **Comment prompt** → Appears for new games only
5. **Learning** → From comment or AI analysis

### Duplicate Detection
- **Game ID**: `opponent_map_duration_date`
- **Prevents**: Re-learning from replay viewing
- **Logs**: "Game already processed, skipping comment prompt"

## Usage

### After Each Game
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

### Comment Examples
- "Always goes roach rush - very predictable"
- "Fast expand into muta tech, standard macro"
- "Early pool aggression, transitions to macro"

### Skip Comment
- Press **Enter** to skip
- AI learns from replay data instead
- No duplicate prompts for same game

## Troubleshooting

### System Not Prompting
- Check `ENABLE_PATTERN_LEARNING = True`
- Verify pattern learner initialized
- Check logs for "Scheduled delayed pattern learning trigger"

### Duplicate Prompts
- **Expected behavior** due to Blizzard API bug
- System will skip due to duplicate detection
- Log: "Game already processed, skipping comment prompt"

### Debug Logs
```
INFO: Pattern learning system initialized with X patterns
INFO: Scheduled delayed pattern learning trigger (15 seconds)
INFO: Replay data available - triggering pattern learning system
INFO: Game already processed, skipping comment prompt
```

## Configuration

### Key Settings
```python
PATTERN_LEARNING_SIMILARITY_THRESHOLD = 0.7  # Pattern matching strictness
PATTERN_LEARNING_MAX_PATTERNS = 1000         # Max patterns per keyword
BUILD_ORDER_COUNT_TO_ANALYZE = 60            # Supply threshold for analysis
```

### Adjustments
- **Higher similarity** = More strict pattern matching
- **Lower max patterns** = Less memory usage
- **Higher supply threshold** = More game data analyzed

## File Locations

### Core System
- `api/pattern_learning.py` - Main learning system
- `api/sc2_game_utils.py` - Game completion handling
- `models/game_info.py` - Blizzard API bug workaround

### Data Storage
- `data/patterns.json` - Learned patterns
- `data/keywords.json` - Keyword associations
- `data/learning_stats.json` - System statistics

### Documentation
- `documentation/SC2_PATTERN_LEARNING_SYSTEM.md` - Full documentation
- `documentation/QUICK_REFERENCE.md` - This file

## Future Fixes

### When Blizzard Fixes Their API
1. Revert `models/game_info.py` workaround
2. Remove duplicate detection (if no longer needed)
3. Update documentation

### Current Status
- ✅ **Working**: Pattern learning for real games
- ✅ **Working**: Duplicate prevention for replays
- ⚠️ **Known Issue**: Blizzard API bug
- 🔧 **Workaround**: Streamer detection + duplicate prevention

---

**Last Updated**: August 2025  
**Version**: 1.1 (Blizzard API Bug Update)  
**System**: SC2 Pattern Learning System
