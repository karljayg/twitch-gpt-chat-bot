# psi_mathison

psi_mathison is an AI orchestration platform that connects game intelligence, AI agents, automation, production systems, and community platforms into a single real-time system.

The project integrates StarCraft II, Twitch, Discord, databases, replay analysis, sound systems, voice systems, OpenAI models, and production workflows. Rather than functioning as a simple chatbot, psi_mathison acts as an intelligent orchestration layer that observes events, maintains context, stores memory, analyzes data, and coordinates actions across multiple services.

Originally developed around StarCraft II and live streaming, the platform has evolved into a broader system for game intelligence, automation, production assistance, AI-driven analysis, and community engagement.

Watch it in action:
https://www.youtube.com/watch?v=gyRU2YE14uU

Contact:
Twitter: https://twitter.com/karljayg
Email: kj (at) psistorm.com

Documentation:
https://docs.google.com/document/d/1C8MM_BqbOYL9W0N0qu0T1g2DS7Uj_a6Vebd6LJLX4yU/edit?usp=sharing

## What It Does

psi_mathison continuously monitors and coordinates information from multiple sources including:

- StarCraft II game events
- Replay files
- Twitch chat
- Discord servers
- Databases
- Voice systems
- Production events
- External APIs

The platform can:

- Analyze live game state
- Track opponents and player history
- Learn strategic patterns
- Generate AI commentary and insights
- Trigger sounds and notifications
- Coordinate Twitch and Discord interactions
- Store and retrieve historical context
- Automate production workflows
- Provide real-time strategic recommendations

## Core Features

### StarCraft II Intelligence

- Live game monitoring
- Replay analysis
- Build order tracking
- Opponent profiling
- Match history analysis
- Strategic pattern recognition
- Race-specific analysis
- Automated game summaries

### AI Orchestration

- OpenAI powered reasoning and responses
- Context aware decision making
- Long-term memory through database storage
- Multi-source information aggregation
- AI generated commentary and analysis
- Agent-based workflow coordination

### Twitch Integration

- Twitch chat interaction
- Event monitoring
- Follow notifications
- Raid notifications
- Subscription notifications
- AI-assisted community engagement

### Discord Integration

- Discord chat interaction
- Shared intelligence across platforms
- Community management support
- Automated notifications and responses

### Pattern Learning System

- Learns from replay history
- Identifies strategic tendencies
- Extracts keywords and patterns
- Stores player comments and observations
- Supports future machine learning workflows
- Continuously improves opponent intelligence

### ML Opponent Analysis

- Live opponent analysis
- Pattern matching against historical games
- Race-aware filtering
- Strategic recommendation generation
- Replay-backed intelligence
- Real-time game preparation

### Voice and Audio Systems

- Speech-to-text support
- Text-to-speech support
- Custom sound triggers
- Production audio automation

### Database and Memory

- Historical player tracking
- Persistent strategic knowledge
- Replay metadata storage
- Opponent intelligence database
- Long-term context management

## Recent Updates

### v1.0.2

- Enhanced ML opponent analysis system
- Improved strategic pattern matching
- Added race-based filtering
- Improved keyword extraction
- Expanded build order analysis
- Added priority scoring for player comments
- Improved Twitch output summaries
- Enhanced analysis testing tools

### v1.0.1

- Fixed opponent name parsing issue
- Corrected pattern learning data storage
- Improved replay intelligence accuracy

## Getting Started

### Requirements

- Python 3.11.4
- pip 23.2.1
- Twitch OAuth Token
- OpenAI API Key
- StarCraft II replay directory
- Database configuration

### Installation

```bash
git clone https://github.com/karljayg/twitch-gpt-chat-bot.git
cd twitch-gpt-chat-bot

pip install virtualenv
virtualenv venv

source venv/Scripts/activate
pip install -r requirements.txt
```

For Linux or macOS:

```bash
source venv/bin/activate
```

If required:

```bash
pip install en-core-web-sm@https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.0.0/en_core_web_sm-3.0.0-py3-none-any.whl
```

## Configuration

Copy:

```bash
cp settings/config.example.py settings/config.py
```

Configure:

- TOKEN
- OPENAI_API_KEY
- DB_USER
- DB_PASSWORD
- REPLAYS_FOLDER
- TEST_MODE

Copy:

```bash
cp settings/SC2_sounds.example.json settings/SC2_sounds.json
```

Initialize the database:

```bash
cd setup
python setup.py
```

Start the platform:

```bash
python app.py
```

## Twitch Chat Trigger

To generate an AI response:

```text
open sesame your message
```

## Testing Opponent Analysis

Analyze a specific opponent:

```bash
python analyze_player.py grumpykitten protoss
```

Analyze all opponents:

```bash
python analyze_player.py all
```

The tool displays:

- Pattern matches
- Similarity scores
- Race filtering
- Strategic summaries
- Expected live output

## Key Concepts

### Context Awareness

Responses can change based on:

- Current game state
- Replay history
- Chat activity
- Stored memory
- Platform events

### Perspective Modes

The system can operate as:

- Commentator
- Analyst
- Fan
- Assistant

### Pattern Learning

The platform continuously builds knowledge from:

- Replay analysis
- Player comments
- Build orders
- Strategic observations
- Historical game results

## Project Structure

```text
twitch-gpt-chat-bot/
├── api/
├── models/
├── settings/
├── setup/
├── sounds/
├── utils/
├── logs/
├── test/
├── data/
├── app.py
├── analyze_player.py
├── requirements.txt
└── README.md
```

## Known Issues

- Random race detection can still be improved
- Persistent memory expansion is ongoing
- Additional data source integration planned
- Further production automation planned

## Future Direction

- Expanded AI agent coordination
- Additional game integrations
- Improved long-term memory systems
- Advanced production automation
- Enhanced Discord workflows
- Expanded machine learning capabilities
- Multi-game intelligence support

## License

MIT License
