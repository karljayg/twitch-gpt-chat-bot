# SC2 Pattern Learning System Documentation

This folder contains comprehensive documentation for the SC2 Pattern Learning System, an intelligent build order analysis and pattern recognition system for StarCraft 2.

## 📚 Documentation Files

### 1. **SC2_PATTERN_LEARNING_SYSTEM.md** - Complete System Documentation
- **Full system overview** and architecture
- **Detailed implementation** guide
- **Configuration options** and settings
- **Troubleshooting** and debugging
- **🚨 BLIZZARD API BUG** documentation and workarounds
- **Duplicate detection** system explanation

### 2. **QUICK_REFERENCE.md** - Fast Setup & Usage Guide
- **Quick start** instructions
- **Common commands** and examples
- **Troubleshooting** quick fixes
- **🚨 Blizzard API bug** current status
- **System behavior** expectations

## 🚨 Important: Blizzard API Bug

**The SC2 localhost JSON API is currently broken** - the `isReplay` field always returns `true` even for real games.

### What This Means
- ✅ **Real games you play** → Pattern learning works correctly
- ⚠️ **Watching replays** → Also detected as "real game" (false positive)
- 🔧 **Duplicate detection** → Prevents re-learning from replay viewing

### Our Workaround
The system now detects real games by checking if the streamer is actually playing, not by the broken `isReplay` flag.

### When Blizzard Fixes It
1. Revert the workaround in `models/game_info.py`
2. Remove duplicate detection (if no longer needed)
3. Update documentation

## 🎯 System Overview

The SC2 Pattern Learning System:
- **Learns from your expert comments** after each game
- **Analyzes replay data** when no comment is provided
- **Provides strategic insights** for repeat opponents
- **Stores patterns persistently** in JSON files
- **Works around Blizzard's broken API** with smart detection

## 🚀 Quick Start

1. **Enable in config**: `ENABLE_PATTERN_LEARNING = True`
2. **System automatically**: Prompts for comments after games
3. **Provide insights**: Use SC2 terminology in your comments
4. **Skip if desired**: Press Enter to let AI learn from replay data
5. **View results**: Check `data/` directory for learned patterns

## 📁 File Structure

```
documentation/
├── README.md                           # This file
├── SC2_PATTERN_LEARNING_SYSTEM.md     # Complete documentation
└── QUICK_REFERENCE.md                 # Quick setup guide

data/                                  # Pattern storage
├── patterns.json                      # Learned patterns
├── keywords.json                      # Keyword associations
└── learning_stats.json                # System statistics

api/                                   # Core system
├── pattern_learning.py                # Main learning system
├── sc2_game_utils.py                 # Game completion handling
└── twitch_bot.py                      # Bot integration
```

## 🔧 Current Status

- ✅ **Pattern Learning**: Working for real games
- ✅ **Duplicate Prevention**: Prevents replay re-learning
- ✅ **Blizzard API Workaround**: Streamer detection + duplicate prevention
- ⚠️ **Known Issue**: Blizzard's broken `isReplay` field
- 🔮 **Future**: Easy to fix when Blizzard fixes their API

## 📖 Reading Order

1. **Start with**: `QUICK_REFERENCE.md` for fast setup
2. **Deep dive**: `SC2_PATTERN_LEARNING_SYSTEM.md` for complete understanding
3. **Reference**: This `README.md` for overview and navigation

## 🆘 Need Help?

### Common Issues
- **System not prompting**: Check config and initialization
- **Duplicate prompts**: Expected behavior due to Blizzard API bug
- **Patterns not saving**: Check file permissions and disk space

### Debug Information
- Check system logs for detailed information
- Examine `data/` directory for pattern files
- Test with simple game scenarios

## 🔮 Future Enhancements

- True machine learning algorithms
- Advanced analytics and win rate correlation
- Meta strategy tracking and analysis
- Visual pattern interface
- External API integration

---

**Last Updated**: August 2025  
**Version**: 1.1 (Blizzard API Bug Update)  
**System**: SC2 Pattern Learning System  
**Status**: Working with API workarounds
