# Mathison Bot - TDD Architecture & Developer Guide

## 1. Architecture Overview

The project has been restructured from a monolithic design into a **Hybrid Modular Architecture**. This ensures legacy stability while enabling modern **Test-Driven Development (TDD)** for all new features.

### 1.1 Core Layers
*   **Core (`core/`)**: The brain of the bot. Contains strictly typed business logic, services, and event handling. Pure Python, no external API dependencies (mocks used for testing).
*   **Adapters (`adapters/`)**: Bridges the clean Core to the dirty outside world (Twitch IRC, Discord API, SC2 Client, OpenAI).
*   **Services (`core/services/`)**: Encapsulated logic for specific domains (Audio, Analysis, Pattern Learning).
*   **Handlers (`core/handlers/`)**: Specific command processors (Wiki, Career, Analyze).
*   **Repositories (`core/repositories/`)**: Data access layer abstraction. Wraps the legacy MySQL class.

### 1.2 Directory Structure
```
root/
├── core/                   # Clean Architecture Core
│   ├── bot.py              # Main Event Loop & Orchestrator
│   ├── events.py           # Event Data Classes (MessageEvent, GameStateEvent)
│   ├── interfaces.py       # Abstract Base Classes (Contracts)
│   ├── command_service.py  # Central Command Dispatcher
│   ├── services/           # Domain Services
│   │   ├── analysis_service.py
│   │   ├── audio_service.py
│   │   └── pattern_learning_service.py
│   ├── handlers/           # Command Handlers
│   │   ├── analyze_handler.py
│   │   ├── career_handler.py
│   │   └── ...
│   └── repositories/       # Database Access
│       ├── sql_player_repository.py
│       └── sql_replay_repository.py
├── adapters/               # External System Wrappers
│   ├── discord_adapter.py
│   ├── twitch_adapter.py
│   └── sc2_adapter.py
├── tests/                  # TDD Test Suite
│   ├── adapters/           # Integration Tests for Adapters
│   ├── handlers/           # Unit Tests for Command Handlers
│   ├── repositories/       # Tests for Data Access
│   ├── scenarios/          # End-to-End Simulation Tests
│   └── services/           # Unit Tests for Services
├── api/                    # Legacy Code (TwitchBot, SC2 Utils)
└── run_core.py             # New Entry Point
```

---

## 2. Test-Driven Development (TDD) Guide

We follow a strict TDD cycle: **Red -> Green -> Refactor**.

### 2.1 Running Tests
To run the full suite:
```bash
pytest -v tests/
```

To run a specific category:
```bash
pytest tests/services/       # Service logic
pytest tests/scenarios/      # End-to-End scenarios
```

### 2.2 Creating a New Feature (Example: "!joke" command)

**Step 1: Define Interface (if needed)**
*   Modify `core/interfaces.py` if you need a new external capability (e.g., `IJokeProvider`).

**Step 2: Write the Test (RED)**
*   Create `tests/handlers/test_joke_handler.py`.
*   Mock dependencies (`ILanguageModel`, `IChatService`).
*   Assert that sending "!joke" results in a specific call/response.
*   *Run test -> Fail (ImportError/AssertionError).*

**Step 3: Implement the Logic (GREEN)**
*   Create `core/handlers/joke_handler.py` implementing `ICommandHandler`.
*   Implement the `handle` method.
*   *Run test -> Pass.*

**Step 4: Wire It Up**
*   In `run_core.py`:
    1. Import `JokeHandler`.
    2. Instantiate it.
    3. Register it: `command_service.register_handler("joke", joke_handler)`.

---

## 3. Integration & Wiring (`run_core.py`)

`run_core.py` is the **Composition Root**. It is the ONLY place where concrete implementations are coupled.

1.  **Initialize Legacy**: Starts `TwitchBot` (threaded) and `DiscordBot` (async).
2.  **Initialize Core**: Creates `BotCore` with Mocks (or Real adapters).
3.  **Create Adapters**: Wraps legacy bots into `TwitchAdapter`, `DiscordAdapter`, `SC2Adapter`.
4.  **Inject Services**:
    *   `AudioService` (wraps TTS/SFX).
    *   `GameResultService` (wraps Replay parsing).
    *   `AnalysisService` (wraps ML Analyzer).
5.  **Register Handlers**: Maps text commands (`!wiki`) to Handlers.
6.  **Start Loop**: Launches the `asyncio` event loop gathering all tasks.

---

## 4. Key Components & Flows

### 4.1 Command Flow
User types `!wiki Starcraft` in Twitch:
1.  **TwitchAdapter** receives message (via Legacy Bot).
2.  Adapter fires `MessageEvent` to `BotCore`.
3.  `BotCore` checks `CommandService`.
4.  `CommandService` matches "wiki".
5.  `WikiHandler` executes (calls LLM/Wiki Utils).
6.  `WikiHandler` sends response via `TwitchAdapter`.

### 4.2 Game Lifecycle Flow
1.  `SC2Adapter` polls SC2 Client API.
2.  Detects `MATCH_STARTED` -> Fires `GameStateEvent`.
3.  `BotCore` handles Start:
    *   Syncs conversation mode.
    *   Generates "Hype Intro" via LLM.
    *   Broadcasts to Twitch/Discord.
4.  Detects `MATCH_ENDED` -> Fires `GameStateEvent` AND triggers `GameResultService`.
5.  `GameResultService`:
    *   Waits for replay file.
    *   Parses Replay.
    *   Saves to DB (`SqlReplayRepository`).
    *   Announces Winner.

### 4.3 Legacy Fallback
If a message is NOT a command (e.g., just chat), `BotCore` ignores it for Twitch (letting Legacy `TwitchBot` handle generic chat/personality), but processes it for Discord (via `DiscordAdapter`). This ensures we don't break existing complex chat behaviors while migrating.

---

## 5. Setup & Installation

### Prerequisites
*   Python 3.11+
*   StarCraft II Client (running)
*   Twitch Account & Token
*   OpenAI API Key
*   Discord Token (Optional)

### Configuration
Ensure `settings/config.py` is populated with your credentials.

### Testing Setup
A `pytest.ini` file is required in the root directory to ensure imports work correctly:
```ini
[pytest]
pythonpath = .
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
testpaths = tests
```

### Running the Bot
```bash
python run_core.py
```

### Troubleshooting
*   **Tests fail?** Check `pytest` installation. Ensure you are in the root directory.
*   **Discord error on exit?** `AttributeError: 'NoneType' object has no attribute 'close'` is a known harmless Windows asyncio cleanup issue. Ignore it.
*   **Bot silent?** Ensure `PLAYER_INTROS_ENABLED=True` or check logs for `BotCore started`.

