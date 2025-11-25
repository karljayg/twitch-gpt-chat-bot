# Quick Start Guide - TDD Architecture

## Start the Bot

```bash
python run_core.py PLAYER_INTROS_ENABLED=False
```

## What to Expect

### Visual Indicators (Heartbeat Symbols)
- `.` = Normal operation (SC2 API polling every 5 seconds)
- `+` = Database heartbeat (every ~60 seconds)
- `w` = Discord last word checker (every ~1 hour)
- `o` = Error (SC2 API failure or connection issue)

**Note:** Discord shard reconnection messages are suppressed (no visual indicator)

### Game Cycle

1. **Start SC2 Game** → Bot detects → Sends intro to Twitch
2. **Play Game** → Bot monitors
3. **End Game** → Bot waits 10s → Parses replay → Saves to DB → Suggests pattern
4. **Type in Twitch**: `player comment <your description>` → Saved!

### Commands (in Twitch chat)

- `player comment <text>` - Save comment about last game
- `!analyze <player>` - Get player stats
- `!wiki <term>` - Search wiki
- Regular chat - OpenAI responds (with dice roll)

## Files to Check

- `temp/last_replay_data.json` - Parsed replay data
- `temp/replay_summary.txt` - Human-readable summary
- `data/patterns.json` - Pattern learning database
- `logs/` - All log files

## Troubleshooting

### Bot not detecting game
- Check SC2 is running
- Check SC2 API is accessible (http://localhost:6119/game)
- Look for `o` indicators (API errors)

### Commands not working
- Verify you're typing in the correct Twitch channel
- Check console logs for errors
- Verify database connection

### Pattern learning not suggesting
- Only works for 1v1 games
- Game must not be abandoned
- Check `data/patterns.json` exists

## Need Help?

Check these files:
1. `IMPLEMENTATION_COMPLETE.md` - Full implementation details
2. `FEATURE_AUDIT.md` - Feature checklist
3. Console logs - Real-time errors

## Rollback to Legacy

If needed:
```bash
python app.py
```


