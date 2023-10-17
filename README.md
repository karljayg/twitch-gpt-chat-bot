# Twitch OpenAI IRC Bot

The "psi_mathison" bot, designed to enhance the experience of watching StarCraft II (SC2) streams, utilizes a combination of technologies, including the Twitch chat interface, OpenAI's GPT models, and the SC2 client for real-time integration. Through monitoring the game states, the bot dynamically interacts with the Twitch chat associated with the stream, responding to user queries, commenting on gameplay, and adding customized engagement through Mood and Perspective settings. 

It incorporates various features such as control over message sending, extensive logging, game state monitoring, and more. By providing analytical insights, humor, or other emotive responses, "psi_mathison" brings a unique and lively dimension to the SC2 viewing experience.

If you have any questions reach out to me at:

https://twitter.com/karljayg  Same tag on instagram, or email me at kj (at) psistorm.com

See its use in one of our recent broadcasts: https://www.youtube.com/watch?v=gyRU2YE14uU

Additional documentation: https://docs.google.com/document/d/1C8MM_BqbOYL9W0N0qu0T1g2DS7Uj_a6Vebd6LJLX4yU/edit?usp=sharing

## Getting Started

### Prerequisites

Before you can use this bot, you will need to:

- Obtain a Twitch account
- Obtain an OAuth token for your Twitch account from https://twitchapps.com/tmi/
- Obtain an OpenAI API key

### Installing

1. Clone this repository to your local machine
2. Install the required Python packages by running:
```
pip install -r requirements.txt
```
   or manually:
```
pip install irc openai logging requests re asyncio random irc.bot spacy nltk en_core_web_sm logging urllib3
python -m spacy download en_core_web_sm
```

3. Set up the configuration file by copying `settings.example.py` to `settings.py` and replacing the placeholders with your own values

### Usage

Initilize DB migration

```
cd setup
```
```
python setup.py
```


To start the bot, run in your terminal:

```
python app.py
```

In your Twitch channel chat, type "open sesame" followed by your message to generate a response from the OpenAI API.

## License


# chan notes(to be removed once done):
   - https://www.youtube.com/watch?v=25P5apB4XWM - 

   - https://www.youtube.com/watch?v=e9yMYdnSlUA - organized python codes
      
   - https://www.youtube.com/watch?v=rp1QR3eGI1k - refactoring tips


### project package/module file structuring
twitch-gpt-chat-bot
    ┣ api
    ┃   ┣ aligulac.py
    ┃   ┗ twitch_bot.py
    ┣ logs
    ┣ models
    ┃   ┣ game_info.py
    ┃   ┣ log_once_within_interval_filter.py
    ┃   ┗ mathison_db.py
    ┣ settings
    ┃   ┣ config.example.py
    ┃   ┣ config.py
    ┃   ┣ SC2_sounds.example.json
    ┃   ┗ SC2_sounds.json
    ┣ setup
    ┃   ┗ setup.sql
    ┣ sound
    ┣ temp
    ┣ test
    ┃   ┗ replays
    ┃   ┗ SC2_game_result_test.json
    ┣ utils
    ┃   ┣ file_utils.py
    ┃   ┣ load_replays.py
    ┃   ┣ sc2replaystats.py
    ┃   ┣ tokensArray.py
    ┃   ┗ wiki_utils.py
    ┣ .gitignore
    ┣ app.py
    ┣ LICENSE.md
    ┣ README.md
    ┣ requirements.txt
    