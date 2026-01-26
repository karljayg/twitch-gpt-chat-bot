# Gemini Project Analysis: psi_mathison

## Project Overview

This project, `psi_mathison`, is a sophisticated chatbot designed for StarCraft II streams, with integrations for both Twitch and Discord. It provides AI-powered commentary, voice interaction, and intelligent replay analysis. The bot leverages OpenAI's GPT models for generating context-aware chat responses and analyzing game data.

The core technologies used are:
- **Language:** Python 3.11
- **AI/ML:** OpenAI, Langchain, Spacy, NLTK
- **Integrations:** Twitch (via IRC), Discord (via discord.py), StarCraft II (via sc2reader, spawningtool)
- **Database:** MySQL

The architecture is transitioning towards a modular, service-oriented design. The main entry point is `app.py`, which launches the Twitch and Discord bots. A newer, TDD-focused architecture is being developed in `run_core.py`, which uses a `BotCore` with adapters for different services. The project has a strong emphasis on machine learning for build order pattern recognition and opponent analysis.

## Building and Running

### Setup

1.  **Create a virtual environment:**
    ```bash
    virtualenv venv
    source venv/bin/activate
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configure the bot:**
    - Copy `settings/config.example.py` to `settings/config.py` and fill in the required API keys and credentials for Twitch, Discord, OpenAI, and your database.
    - Copy `settings/SC2_sounds.example.json` to `settings/SC2_sounds.json`.

4.  **Initialize the database:**
    ```bash
    cd setup
    python setup.py
    ```

### Running the Bot

- **To run the main application:**
  ```bash
  python app.py
  ```
- **To run with player intros enabled (example from `start_mathison.sh`):**
  ```bash
  python app.py PLAYER_INTROS_ENABLED=true
  ```

### Running Tests

- **To run all tests:**
  ```bash
  ./run_all_tests.sh
  ```
  or
  ```bash
  python -m pytest tests/ -v --tb=short -o log_cli=true -o log_cli_level=INFO
  ```

## Development Conventions

- **Modular Architecture:** The project is moving towards a core logic module (`core/`) with adapters for external services (`adapters/`). New features should likely follow this pattern.
- **Testing:** The project uses `pytest` for testing. The `run_all_tests.sh` script suggests a standard way to run tests with verbose output. Test-Driven Development (TDD) is mentioned in the `README.md` as a key development practice, particularly for the pattern learning system.
- **Configuration:** All configuration is managed in `settings/config.py`. Avoid hardcoding credentials or settings in the source code.
- **Dependencies:** Project dependencies are managed in `requirements.txt`.
- **Database Schema:** The database schema is defined in `setup/init_schema_up.sql` and `setup/setup.sql`. Changes to the database should be reflected here.
