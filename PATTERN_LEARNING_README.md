# SC2 Pattern Learning System

## Overview

The SC2 Pattern Learning System is an intelligent bot feature that learns StarCraft 2 build patterns from your expert comments and replay data. Instead of hardcoded rules, it learns from your natural language descriptions to recognize strategies and provide intelligent analysis.

## How It Works

### 1. **Dual Learning Process**
After each game ends, the bot prompts you to enter a comment about the game:

**With Your Comment:**
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

**Without Your Comment:**
- AI automatically analyzes the replay data
- Learns patterns from build orders, timings, and unit production
- Stores insights as "AI detected: [strategy]"

### 2. **Pattern Recognition**
The system extracts SC2 strategy keywords from your comments:
- **Strategy terms**: rush, macro, tech, timing, all-in, cheese
- **Unit terms**: zergling, roach, hydra, marine, marauder, zealot
- **Race-specific terms**: pool (zerg), barracks (terran), gateway (protoss)

### 3. **Build Signature Creation**
For each comment, it creates a "fingerprint" of the build order:
- Early game (first 20 supply)
- Mid game (20-80 supply) 
- Late game (80+ supply)
- Key building timings
- Unit production patterns
- Building sequence

### 4. **Pattern Matching & Opponent Insights**
When a new game starts, it provides insights based on learned patterns:

**Build Pattern Recognition:**
```
🎯 Pattern Analysis Results:
  zergling_rush: 87% confidence
    Sample: Classic zergling rush - pool first, speed, all-in aggression
    Based on 3 previous games
```

**Opponent-Specific Insights:**
```
🎯 PlayerX tends to do zergling rush - you noted this before
🤖 I think based on previous games vs. PlayerY, they tend to do reaper harass
```

## Configuration

### Enable/Disable
```python
# In settings/config.py
ENABLE_PATTERN_LEARNING = True  # Set to False to disable
```

### Adjust Sensitivity
```python
PATTERN_LEARNING_SIMILARITY_THRESHOLD = 0.7  # 70% similarity required
PATTERN_LEARNING_MAX_PATTERNS = 1000  # Max patterns to store
```

## Enhanced Learning Cycle

### **Phase 1: Expert Learning (Your Comments)**
**Game 1**: You comment "Classic zergling rush - pool first, speed, all-in aggression"
**System learns**: "zergling rush" = early pool + speed + zergling spam
**Source**: Your expert insight

### **Phase 2: AI Learning (Replay Analysis)**
**Game 2**: No comment provided
**AI analyzes**: Pool at 12 supply → Zerglings → Speed
**AI learns**: "AI detected: Zergling rush" (75% confidence)
**Source**: AI analysis of replay data

### **Phase 3: Pattern Recognition**
**Game 3**: New game vs. PlayerX (repeat opponent)
**System provides**: "🎯 PlayerX tends to do zergling rush - you noted this before"
**Source**: Your expert comment from Game 1

### **Phase 4: AI-Generated Insights**
**Game 4**: New game vs. PlayerY (repeat opponent, no previous comments)
**System provides**: "🤖 I think based on previous games vs. PlayerY, they tend to do reaper harass"
**Source**: AI learning from Game 2 replay data

## Benefits

✅ **Learns from your expertise** - not hardcoded assumptions  
✅ **AI learns from replay data** - even when you don't comment  
✅ **Opponent-specific insights** - recognizes repeat players and their tendencies  
✅ **Clear source attribution** - distinguishes your expert insights from AI learning  
✅ **Continuous improvement** - every game makes it smarter  
✅ **Natural language** - uses your SC2 vocabulary  

## Usage Tips

### **Good Comments** (teach the system):
- "Early game aggression with reaper harass"
- "Macro-focused zerg - multiple hatcheries, economic play"
- "Tech rush to carriers, skipped ground units"
- "Timing attack at 8 minutes with stim marines"

### **Avoid** (too vague):
- "Good game"
- "Fun match"
- "Close game"

### **Skip Comments**:
- Press Enter to skip if you don't have time
- The system continues learning from other games
- No penalty for skipping

## Technical Details

### **Pattern Storage**
- Patterns stored in memory during runtime
- Can be extended to save to database for persistence
- Configurable memory limits

### **Similarity Algorithm**
- **40% weight**: Early game build order
- **30% weight**: Building sequence
- **30% weight**: Key timing windows (±30 seconds)

### **Performance**
- Non-blocking input prompts
- Graceful error handling
- Minimal impact on bot operation

## Testing

Run the test script to see the system in action:
```bash
python test_pattern_learning.py
```

This demonstrates:
- Learning from sample games
- Pattern recognition
- Similarity scoring
- Statistics reporting

## Integration Points

The system integrates with:
- **Game End Handler**: Prompts for comments after each game
- **Replay Analysis**: Uses build order data from replays
- **Database**: Can store comments and patterns persistently
- **Chat System**: Provides intelligent strategy analysis

## Future Enhancements

- **Database persistence** for patterns across bot restarts
- **Advanced ML algorithms** for better pattern recognition
- **Strategy recommendations** based on learned patterns
- **Meta analysis** across different maps and matchups
- **Export/import** of learned patterns

## Troubleshooting

### **Bot not prompting for comments?**
- Check `ENABLE_PATTERN_LEARNING = True` in config
- Verify pattern learning module imported successfully
- Check logs for initialization errors

### **Comments not being processed?**
- Ensure game data includes build order information
- Check logs for processing errors
- Verify database connection if using persistence

### **Pattern matching not working?**
- Adjust `PATTERN_LEARNING_SIMILARITY_THRESHOLD` (try 0.6-0.8)
- Check that comments contain recognizable SC2 keywords
- Verify build order data format

---

**The system becomes your SC2 apprentice, learning from thousands of replays and your expert insights to provide intelligent strategy analysis!**
