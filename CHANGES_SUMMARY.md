# Changes Summary Since Last Commit

## 1. Fixed "First Match" Message Bug (game_started_handler.py)

**Issue**: The message incorrectly used `streamer_picked_race` (from previous game) instead of `streamer_current_race` (from current game), causing messages like "Protoss vs Protoss" when it should be "Zerg vs Protoss".

**Fix**: Changed lines 460 and 463 to use `streamer_current_race` for the current game matchup.

**Files Changed:**
- `api/game_event_utils/game_started_handler.py` (lines 460, 463)

---

## 2. Split Build Order Config into Two Values

**Issue**: `BUILD_ORDER_COUNT_TO_ANALYZE` was being used for two incompatible purposes:
- Step count (array slicing) - should be 120
- Supply threshold (filtering) - should be 60

**Fix**: Split into two config values:
- `BUILD_ORDER_STEPS_TO_ANALYZE = 120` - for step counts (pattern signatures, matching, DB extraction)
- `EARLY_GAME_SUPPLY_THRESHOLD = 60` - for supply-based filtering (early game classification)

**Files Changed:**
- `settings/config.py` - Added new configs, removed old one
- `settings/config.example.py` - Added new configs, removed old one
- `api/pattern_learning.py`:
  - Line 275: Changed to `EARLY_GAME_SUPPLY_THRESHOLD` (supply filtering)
  - Line 306: Changed to `EARLY_GAME_SUPPLY_THRESHOLD` (supply filtering)
  - Line 446: Changed to `BUILD_ORDER_STEPS_TO_ANALYZE` (step count)
- `models/mathison_db.py` (line 762): Changed to `BUILD_ORDER_STEPS_TO_ANALYZE`
- `utils/load_replays.py` (line 168): Changed to `BUILD_ORDER_STEPS_TO_ANALYZE`
- `api/game_event_utils/game_started_handler.py` (line 194): Updated comment

---

## 3. Fixed Pattern Learning Context Expiration Bug

**Issue**: When pattern learning context expired after 5 minutes, the code still tried to access `ctx['pattern_match']` on a `None` object, causing `TypeError: 'NoneType' object is not subscriptable`.

**Fix**: 
- Added early return in `chat_utils.py` when context expires (so function isn't called)
- Added defensive check in `_process_natural_language_pattern_response()` to handle `None` context

**Files Changed:**
- `api/chat_utils.py` (line 337): Added return statement when context expires
- `api/twitch_bot.py` (line 1045): Added None check and return ('skip', None)

---

## Summary

**Total Files Modified**: 6
1. `api/game_event_utils/game_started_handler.py` - Fixed race mismatch bug + config update
2. `settings/config.py` - Split config
3. `settings/config.example.py` - Split config  
4. `api/pattern_learning.py` - Updated to use split configs
5. `models/mathison_db.py` - Updated config reference
6. `utils/load_replays.py` - Updated config reference
7. `api/chat_utils.py` - Fixed NoneType bug
8. `api/twitch_bot.py` - Fixed NoneType bug

**Note**: Analysis documents created (BUILD_ORDER_STEP_ANALYSIS.md, BREAKING_CHANGES_ANALYSIS.md) are for reference only and not part of code changes.

