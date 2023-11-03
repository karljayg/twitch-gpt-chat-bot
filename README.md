# Twitch OpenAI IRC Bot

The "psi_mathison" bot, designed to enhance the experience of watching StarCraft II (SC2) streams, utilizes a combination of technologies, including the Twitch chat interface, OpenAI's GPT models, and the SC2 client for real-time integration. Through monitoring the game states, the bot dynamically interacts with the Twitch chat associated with the stream, responding to user queries, commenting on gameplay, and adding customized engagement through Mood and Perspective settings. 

It incorporates various features such as control over message sending, extensive logging, game state monitoring, and more. By providing analytical insights, humor, or other emotive responses, "psi_mathison" brings a unique and lively dimension to the SC2 viewing experience.

If you have any questions reach out to me at:

https://twitter.com/karljayg  Same tag on instagram, or email me at kj (at) psistorm.com

See its use in one of our recent broadcasts: https://www.youtube.com/watch?v=gyRU2YE14uU

Additional documentation: https://docs.google.com/document/d/1C8MM_BqbOYL9W0N0qu0T1g2DS7Uj_a6Vebd6LJLX4yU/edit?usp=sharing

## Getting Started

### Prerequisites

Before you can use this bot, you will need to have:
   1. Python Version 3.11.4
   2. pip version 23.2.1
   3. Twitch Account
	   a. To create twitch account go to https://www.twitch.tv/ and sign up.
	   b. Then obtain OAuth token / Twitch Chat Auth go to https://twitchapps.com/tmi/
   4. OpenAI Key	
      a. Create OpenAI Account using https://openai.com/
      b. Navigate to your profile then choose View API Keys
      c. Create API Key



### Installing

1. Clone this repository to your local machine
   - git clone https://github.com/karljayg/twitch-gpt-chat-bot.git
   - cd /path/to/repository
   - git branch -a
   - git checkout branch_name

2. Create Environment
   - Navigate to directory
      cd /path/to/repository
   - Install virtualenv (If not yet installed)
      pip install virtualenv
   - Create new virtual environment (example name: venv)
      virtualenv venv
   - Activate the virtual environment
      source venv/Scripts/activate
   Once activated, the terminal prompt should change to show name of the virtual environment.

3. Install the required Python packages by running:
   ```
   pip install -r requirements.txt
   ```
      or manually:
   ```
   pip install irc openai logging requests re asyncio random irc.bot spacy nltk en_core_web_sm logging urllib3
   python -m spacy download en_core_web_sm
   ```
   If there are errors encountered related to wheel binding try installing this package first before the others:
   ```
   pip install en-core-web-sm@https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.0.0/en_core_web_sm-3.0.0-py3-none-any.whl
```


4. After installing all the required packages, create `config.py` file under settings folder
   Copy the contents of `config.example.py` then change the following configurations
   And edit the settings below:

   - Twitch Settings
      `TOKEN = "twitch token"`
   - OpenAI Settings
      `OPENAI_API_KEY = "sk-open AI Key"`
   - DB Settings
      `DB_USER = "root"`
      `DB_PASSWORD = ""`
   - SC2 Settings - Change the directory to  StarScraft Account folder
      `REPLAYS_FOLDER = "C:\path\to\StarCraft II\Accounts"`
   - If SCII is running, set
      `TEST_MODE = True`
      else
      `TEST_MODE = False`

5. Create SC2_sounds.json
   Just copy the contents of SC2_sound.example.json

6. Create the database
   Initilize DB migration

   ```
   cd setup
   ```
   ```
   python setup.py
   ```

7. To start the bot, run in your terminal:

```
python app.py
```

In your Twitch channel chat, type "open sesame" followed by your message to generate a response from the OpenAI API.

## License


# chan notes(to be removed once done):
   - https://www.youtube.com/watch?v=25P5apB4XWM - 

   - https://www.youtube.com/watch?v=e9yMYdnSlUA - organized python codes
      
   - https://www.youtube.com/watch?v=rp1QR3eGI1k - refactoring tips

   - https://www.youtube.com/watch?v=8rynRTOr4mE -  state management


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
    