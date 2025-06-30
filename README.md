# 🧠 psi_mathison – Twitch + Discord GPT Chatbot for SC2

Enhance your StarCraft II Twitch (and Discord) streams with AI-powered commentary, voice interaction, and replay intelligence. `psi_mathison` leverages OpenAI, Langchain, and custom SC2 logic to provide a smart, immersive experience for viewers.

▶️ **Watch it in action:** [FSL Broadcast Example](https://www.youtube.com/watch?v=gyRU2YE14uU)  
📧 **Contact:** [Twitter](https://twitter.com/karljayg) | Email: kj (at) psistorm.com  
📄 **Docs:** [Full Documentation (Google Doc)](https://docs.google.com/document/d/1C8MM_BqbOYL9W0N0qu0T1g2DS7Uj_a6Vebd6LJLX4yU/edit?usp=sharing)

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
│   └── SC2_game_result_test.json
├── utils/
│   ├── emote_utils.py
│   ├── file_utils.py
│   ├── load_replays.py
│   ├── sc2replaystats.py
│   └── sound_player_utils.py
├── app.py
├── LICENSE.md
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

---

## 🧠 Development Notes

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

