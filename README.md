# 🧠 psi_mathison – Twitch + Discord GPT Chatbot for SC2

Enhance your StarCraft II Twitch (and Discord) streams with AI-powered commentary, voice interaction, and replay intelligence. `psi_mathison` leverages OpenAI, Langchain, and custom SC2 logic to provide a smart, immersive experience for viewers.

▶️ **Watch it in action:** [FSL Broadcast Example](https://www.youtube.com/watch?v=gyRU2YE14uU)  
📧 **Contact:** [Twitter](https://twitter.com/karljayg) | Email: kj (at) psistorm.com  
📄 **Docs:** [Full Documentation (Google Doc)](https://docs.google.com/document/d/1C8MM_BqbOYL9W0N0qu0T1g2DS7Uj_a6Vebd6LJLX4yU/edit?usp=sharing)

## 🆕 Recent Updates

### v1.0.2 - ML Analysis System & Pattern Learning Enhancements
- **Enhanced**: ML opponent analysis system with intelligent pattern matching
- **Fixed**: Player comment priority system for strategic analysis
- **Added**: Race-based pattern filtering using comprehensive SC2 terminology
- **Improved**: Keyword extraction to include 2-character strategic terms (DT, GG, etc.)
- **Enhanced**: Build order analysis to examine full 60-step sequences
- **Added**: Comment priority boost system (+100% for exact matches, +50% for keyword overlap)
- **Fixed**: Strategic conflict detection removed for natural pattern recognition
- **Added**: Concise summary generation for Twitch chat output
- **Enhanced**: Test script (`analyze_player.py`) with top 3 pattern display

### v1.0.1 - Player Name Truncation Fix
- **Fixed**: Pattern learning system was truncating opponent names to single letters
- **Issue**: "eGaliza" → "e", "Muskul" → "M" due to string iteration bug
- **Solution**: Proper comma-separated string parsing in opponent name extraction
- **Impact**: Pattern learning now correctly captures full opponent names

---

## ✨ Features

### 💬 Chat Integration (Twitch & Discord)
- Monitors and replies in Twitch chat and Discord
- Shared logic but separated threads for both platforms
- GPT-powered context-aware chat
- Responds to Follows, Raids, Subs, Donations

### 🎮 SC2 Game Integration
- Live monitoring of match state (start, end, players, results)
- Logs build orders, units lost, and duration
- Summarizes replays and game history

### 🗣 Voice Interaction
- Whisper (Speech-to-Text) input triggers
- Text-to-Speech for short bot messages
- Customizable in-game sound cues (start, win, abandon)

### 🤖 AI-Enhanced Responses
- ChatGPT with Mood + Perspective settings
- Persistent memory per player (WIP)
- Langchain and Liquipedia integration planned

### 📊 Replay Intelligence
- Historical player tracking
- Summaries by opponent, race, and alias
- Matchup-specific notes and outcomes

### 🧠 **Pattern Learning System** *(ENHANCED)*
- **Intelligent Build Order Analysis**: Learns from your SC2 expertise
- **Strategic Pattern Recognition**: Identifies opponent tendencies
- **Machine Learning Ready**: Optimized data structure for future ML integration
- **Test-Driven Development**: Comprehensive test coverage for reliability
- **Dual Comment Storage**: Preserves authentic input while enabling analysis
- **Enhanced Keyword Extraction**: Now includes 2-character strategic terms (DT, GG, APM)

### 🤖 **ML Opponent Analysis System** *(NEW)*
- **Live Game Analysis**: Provides strategic insights at game start via Twitch chat
- **Pattern Matching Engine**: Matches current opponent builds against learned strategies
- **Player Comment Priority**: Gives absolute priority to your actual strategy descriptions
- **Race-Based Filtering**: Uses comprehensive SC2 terminology for accurate race detection
- **Concise Chat Output**: Generates readable summaries like "ML Analysis: grumpykitten (protoss) - Build: Forge → PhotonCannon → DarkShrine - Strategy: cannon rush into DT to collosus"
- **Database Integration**: Falls back to replay analysis when no commented games exist
- **Test Script**: `analyze_player.py` for testing and debugging ML analysis

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11.4
- pip 23.2.1
- Twitch OAuth: [Generate Token](https://twitchapps.com/tmi/)
- OpenAI API Key: [openai.com](https://openai.com/)

### Installation

```bash
git clone https://github.com/karljayg/twitch-gpt-chat-bot.git
cd twitch-gpt-chat-bot
pip install virtualenv
virtualenv venv
source venv/Scripts/activate  # or `source venv/bin/activate` for macOS/Linux
pip install -r requirements.txt
```

If needed, install this first:
```bash
pip install en-core-web-sm@https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.0.0/en_core_web_sm-3.0.0-py3-none-any.whl
```

---

## ⚙️ Configuration

1. Copy `settings/config.example.py` to `config.py` and fill in:
   - `TOKEN`, `OPENAI_API_KEY`, `DB_USER`, `DB_PASSWORD`, `REPLAYS_FOLDER`, `TEST_MODE`

2. Copy `SC2_sounds.example.json` to `SC2_sounds.json`

3. Initialize the database:
```bash
cd setup
python setup.py
```

4. Start the bot:
```bash
python app.py
```

**Tip:** In Twitch chat, use `"open sesame <message>"` to get a reply.

---

## 🧠 Key Concepts

- **Mood Settings:** Cheerful, Sarcastic, Analytical, etc.
- **Perspective Modes:** Commentator, Fan, Analyst
- **Context-Aware Mode:** Adjusts replies based on game status

---

## 🗂 Project Structure

```
twitch-gpt-chat-bot/
├── api/
├── logs/
├── models/
├── settings/
├── setup/
├── sound/
├── temp/
├── test/
├── utils/
├── app.py
├── requirements.txt
├── README.md
├── LICENSE.md
```

---

## 🧪 Known Issues / TODOs

- Improve Random race detection in replays
- Persistent memory across chat sessions (WIP)
- Liquipedia/Subreddit filtering required
- Token budgeting (future feature)

---

## 📄 License

MIT License. See `LICENSE.md`.

---

## 🛠 Maintenance

To update deprecated models (e.g., Langchain):
```bash
pip install --upgrade langchain
```
---

## 📦 Additional Setup and Configuration Details

### Manual Package Installation (alternative to requirements.txt)

If `pip install -r requirements.txt` fails, you may manually install dependencies:
```bash
pip install irc openai logging requests re asyncio random irc.bot spacy nltk en_core_web_sm logging urllib3
python -m spacy download en_core_web_sm
```

If errors occur related to wheel binding:
```bash
pip install en-core-web-sm@https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.0.0/en_core_web_sm-3.0.0-py3-none-any.whl
```

### Replay Directory

Set your SC2 replay folder in `config.py`:
```python
REPLAYS_FOLDER = "C:\path\to\StarCraft II\Accounts"
```

Set `TEST_MODE = True` if SC2 is running; else set it to `False`.

---

## 🧾 Extra Notes

- See organized Python techniques:
  - [Refactoring Tips](https://www.youtube.com/watch?v=rp1QR3eGI1k)
  - [State Management](https://www.youtube.com/watch?v=8rynRTOr4mE)
  - [Code Organization](https://www.youtube.com/watch?v=e9yMYdnSlUA)

---

## 📁 Full File Structure

```
twitch-gpt-chat-bot/
├── api/
│   ├── aligulac.py
│   ├── chat_utils.py
│   ├── discord_bot.py
│   ├── game_event_utils.py
│   ├── ml_opponent_analyzer.py      # 🤖 ML Opponent Analysis System
│   ├── pattern_learning.py          # 🧠 Pattern Learning System
│   ├── sc2_game_utils.py
│   ├── sgreplay_pb2.py
│   ├── stormgate.py
│   ├── text2speech.py
│   └── twitch_bot.py
├── logs/
├── models/
│   ├── game_info.py
│   ├── log_once_within_interval_filter.py
│   └── mathison_db.py
├── settings/
│   ├── aliases.py
│   ├── config.example.py
│   ├── config.py
│   ├── SC2_sounds.example.json
│   └── SC2_sounds.json
├── setup/
│   ├── init_schema_down.sql
│   ├── init_schema_up.sql
│   ├── setup.py
│   └── setup.sql
├── sounds/
├── temp/
├── test/
│   ├── replays/
│   ├── SC2_game_result_test.json
│   └── test_pattern_learning_improvements.py  # 🧪 TDD Test Suite
├── data/
│   ├── comments.json                 # 📝 Player comments and keywords
│   ├── patterns.json                 # 🧠 Learned strategic patterns
│   ├── learning_stats.json           # 📊 Pattern learning statistics
│   └── sc2_race_data.json           # 🏆 Comprehensive SC2 terminology
├── utils/
│   ├── emote_utils.py
│   ├── file_utils.py
│   ├── load_learning_data.py        # 🔄 Pattern data regeneration
│   ├── load_replays.py
│   ├── sc2replaystats.py
│   └── sound_player_utils.py
├── analyze_player.py                  # 🧪 ML Analysis Test Script
├── app.py
├── LICENSE.md
├── PATTERN_LEARNING_IMPROVEMENTS.md  # 📚 Pattern Learning Documentation
├── README.md
├── requirements.txt
```

---

## 🛠 Additional Notes from Original README

### 📌 Twitch & OpenAI Setup (Expanded)

1. **Twitch Account Setup**
   - Visit [https://www.twitch.tv/](https://www.twitch.tv/) and create an account.
   - Generate an OAuth token for Twitch Chat Authentication: [https://twitchapps.com/tmi/](https://twitchapps.com/tmi/)

2. **OpenAI API Setup**
   - Sign up at [https://openai.com/](https://openai.com/)
   - Go to your profile > "View API Keys" > Create a new key.

### 🔄 Git Branch Setup

After cloning the repo, optionally view and check out a specific branch:

```bash
git branch -a
git checkout branch_name
```

### 🧪 Twitch Chat Trigger

To engage the bot via Twitch, type in chat:
```
open sesame <your message>
```
This triggers a reply from the OpenAI-powered assistant.

### 🤖 ML Analysis Testing

Test the ML opponent analysis system using the test script:
```bash
# Test specific opponent
python analyze_player.py grumpykitten protoss

# Test multiple opponents
python analyze_player.py all
```

The script shows:
- Raw pattern matching data
- Top 3 strategic patterns found
- Similarity scores and race filtering
- What would appear in Twitch chat during live games

---

## 🧠 Development Notes

### 🧪 **Pattern Learning System Development**
The pattern learning system was developed using **Test-Driven Development (TDD)**:

- **Test Suite**: `test_pattern_learning_improvements.py` (6 comprehensive tests)
- **Coverage**: Build order structure, comment storage, keyword extraction
- **Approach**: Red-Green-Refactor cycle for reliable development
- **Documentation**: `PATTERN_LEARNING_IMPROVEMENTS.md` for detailed implementation

### 📚 **Documentation**
- **`SC2_PATTERN_LEARNING_SYSTEM.md`**: Main system documentation
- **`PATTERN_LEARNING_IMPROVEMENTS.md`**: Recent improvements and TDD approach
- **Test files**: Living documentation of intended behavior

### 📊 **Data Files**
- **`data/comments.json`**: Player comments and extracted keywords
- **`data/patterns.json`**: Learned strategic patterns from gameplay
- **`data/learning_stats.json`**: Pattern learning statistics and metrics
- **`data/sc2_race_data.json`**: Comprehensive SC2 terminology for race filtering

### 🎯 **Key Improvements Made**
1. **Build Order Consolidation**: Efficient unit grouping with metadata
2. **Dual Comment Storage**: Raw + cleaned comment preservation
3. **Enhanced Keyword Extraction**: Clean, deduplicated strategic terms
4. **ML Readiness**: Structured data format for future machine learning

### 🚀 **ML Analysis System Features**
1. **Live Game Integration**: Automatically analyzes opponents at game start
2. **Pattern Priority System**: Player comments get absolute priority (+100% boost)
3. **Race-Based Filtering**: Comprehensive SC2 terminology for accurate classification
4. **Concise Output**: Generates readable summaries for Twitch chat
5. **Database Fallback**: Works with replay data when no comments exist
6. **Test-Driven Development**: Comprehensive testing with `analyze_player.py`

Helpful developer reference videos:

- [Organized Python Code](https://www.youtube.com/watch?v=e9yMYdnSlUA)
- [Refactoring Tips](https://www.youtube.com/watch?v=rp1QR3eGI1k)
- [State Management](https://www.youtube.com/watch?v=8rynRTOr4mE)
- [Code Patterns in Practice](https://www.youtube.com/watch?v=25P5apB4XWM)

---

## 📁 Other File Mentions

The following was also included in the prior structure and may still be relevant:

```
├── .gitignore
```

