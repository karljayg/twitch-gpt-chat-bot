# Twitch OpenAI IRC Bot

This is an IRC bot for Twitch that uses OpenAI's GPT-3.5 API to generate text responses to messages in chat.

If you have any questions reach out to me at:

https://twitter.com/karljayg  Same tag on instagram, or email me at kj (at) psistorm.com

See its use in one of our recent broadcasts: https://www.youtube.com/watch?v=gyRU2YE14uU

## Getting Started

### Prerequisites

Before you can use this bot, you will need to:

- Obtain a Twitch account
- Obtain an OAuth token for your Twitch account from https://twitchapps.com/tmi/
- Obtain an OpenAI API key

### Installing

1. Clone this repository to your local machine
2. Install the required Python packages by running `pip install -r requirements.txt`
3. Set up the configuration file by copying `settings.example.py` to `settings.py` and replacing the placeholders with your own values

### Usage

To start the bot, run `python bot.py` in your terminal.

In your Twitch channel chat, type "open sesame" followed by your message to generate a response from the OpenAI API.

## License

This project is licensed under the MIT License - see the LICENSE.md file for details.