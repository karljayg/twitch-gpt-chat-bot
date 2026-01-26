# Config Comparison: config.py vs config.example.py

## Missing/Incorrect in config.example.py

### 1. Twitch Settings
- **CLIENT_SECRET**: Missing entirely - should be added as empty string
- **BOT_COMMANDS** line 12: Example has "games in <hrs>" but config.py has "games in last <hrs>" - should match config.py

### 2. Discord Settings
- **DISCORD_ENABLED**: Example has `True`, config.py has `False` (more common for server deployments)
- **DISCORD_CHANNEL_ID**: Example has `None`, should have comment showing it's an integer

### 3. OpenAI Settings
- **ENGINE**: Example has `"gpt-3.5-turbo"`, config.py uses `"gpt-4.1-nano"` - example should probably show current default
- Missing commented ENGINE options that are in config.py (gpt-4-32k, gpt-4)

### 4. SC2 Settings - Critical Missing Items
- **TEST_MODE**: Example has `True`, config.py has `False` - False is production default
- **IGNORE_GAME_STATUS_WHILE_WATCHING_REPLAYS**: Example has `False`, config.py has `True` - True is correct for watching replays
- **PLAYER_INTROS_ENABLED**: Example has `True`, config.py has `False`
- **BRACKET**: Missing entirely - should be added with placeholder text

### 5. Bot Behavior Settings
- **RESPONSE_PROBABILITY**: Example has `0.7`, config.py has `0.2` - 0.2 is current production value
- **MONITOR_GAME_SLEEP_SECONDS**: Example has `7`, config.py has `5` - 5 is current value
- **GREETINGS_LIST_FROM_OTHERS**: Missing 'HeyGuys' that's in config.py
- **IGNORE list**: Missing 'sc2replaystatsbot' that's in config.py

### 6. Audio Settings - Missing Items
- **TEXT_TO_SPEECH**: Example has `True`, config.py has `False` - False is production default
- **ENABLE_SPEECH_TO_TEXT**: Example has `True`, config.py has `False` - False is production default

### 7. SC2 Monitoring Settings - Missing Entire Section
- **ENABLE_SC2_MONITORING_ENHANCED**: Missing - should be `True`
- **SC2_API_TIMEOUT_SECONDS**: Missing - should be `3`
- **SC2_MAX_CONSECUTIVE_FAILURES**: Missing - should be `10`
- **SC2_WATCHDOG_INTERVAL_MINUTES**: Missing - should be `5`

### 8. FSL Integration Settings
- **FSL_API_URL**: Example has localhost, config.py has production URL - example should show both commented
- **FSL_REVIEWER_WEIGHT**: Example has `1.0`, config.py has `0.5` - 0.5 is current value
- **FSL_VERIFY_SSL**: Missing entirely - should be `False` with comment

### 9. Pattern Learning Settings
- **PATTERN_LEARNING_DELAY_SECONDS**: Example has `3`, config.py has `10` - 10 is current value (wait for replay processing)

### 10. SC2_STRATEGIC_ITEMS - Missing Documentation/Comments
Config.py has detailed comments explaining:
- Why certain units/buildings are excluded (e.g., "Drone, Overlord excluded - every Zerg makes these")
- What defines strategy (e.g., "Hatchery timing/count is KEY for expansion style")
- Example has much less detailed comments

### 11. PERSPECTIVE_OPTIONS - Missing Updates
Config.py has more detailed anti-hallucination instructions in several options that aren't in example

### 12. Other Integrations
- **ALIGULAC_API_KEY**: Example has empty string (good), config.py has real key (should stay empty in example)
- **SC2REPLAY_STATS_***: All should remain empty in example (they are)

## Recommended Updates to config.example.py

1. Add missing SC2 monitoring settings (enhanced monitoring, timeout, watchdog)
2. Update production defaults (TEST_MODE=False, RESPONSE_PROBABILITY=0.2, etc.)
3. Add BRACKET setting
4. Add FSL_VERIFY_SSL
5. Update PATTERN_LEARNING_DELAY_SECONDS to 10
6. Add CLIENT_SECRET (empty)
7. Update SC2_STRATEGIC_ITEMS comments to match config.py's detailed explanations
8. Update PERSPECTIVE_OPTIONS to match config.py's anti-hallucination wording
9. Fix BOT_COMMANDS to include "last" in "games in last <hrs>"
10. Add missing items to IGNORE and GREETINGS_LIST_FROM_OTHERS



