import irc.bot
import requests
import logging
import openai
import re
from settings import config

class TwitchBot(irc.bot.SingleServerIRCBot):
    def __init__(self, username, token, channel):
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
        file_handler = logging.FileHandler('bot.log')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Set bot configuration
        self.token = config.TOKEN
        self.channel = config.CHANNEL
        self.username = config.USERNAME
        self.server = config.HOST
        self.port = config.PORT
        openai.api_key = config.OPENAI_API_KEY

        # Initialize the IRC bot
        irc.bot.SingleServerIRCBot.__init__(self, [(self.server, self.port, 'oauth:'+self.token)], self.username, self.username)

    def on_welcome(self, connection, event):
        # Join the channel and say hello
        self.logger.debug('Connected to Twitch IRC server')
        connection.join(self.channel)
        self.logger.debug('Joining channel %s', self.channel)
        greeting_message = 'hello hello'
        connection.privmsg(self.channel, greeting_message)
        self.logger.debug('Sending message: %s', greeting_message)

    def on_pubmsg(self, connection, event):
        # Get message from chat
        msg = event.arguments[0].lower()
        sender = event.source.split('!')[0]

        # Send response to greeting
        if 'hello' in msg:
            response = f"Hi {sender}!"
            connection.privmsg(self.channel, response)
            self.logger.debug('Sending message: %s', response)

        # Send response to OpenAI query
        if 'open sesame' in msg:
            completion = openai.ChatCompletion.create(
            model=config.ENGINE,
            messages=[
                {"role": "user", "content": msg}
            ]
            )
            if completion.choices[0].message!=None:
                print(completion.choices[0].message.content)
                response = f"Hi {sender}! {completion.choices[0].message.content}"

                # Clean up response
                print('raw response from OpenAI: %s', response)
                response = re.sub('[\r\n\t]', ' ', response)  # Remove carriage returns, newlines, and tabs
                response = re.sub('[^\x00-\x7F]+', '', response)  # Remove non-ASCII characters
                response = re.sub(' +', ' ', response) # Remove extra spaces
                response = response.strip() # Remove leading and trailing whitespace

                # Split the response into chunks of 400 characters, without splitting the words
                chunks = []
                temp_chunk = ''
                for word in response.split():
                    if len(temp_chunk + ' ' + word) <= 400:
                        temp_chunk += ' ' + word if temp_chunk != '' else word
                    else:
                        chunks.append(temp_chunk)
                        temp_chunk = word
                if temp_chunk:
                    chunks.append(temp_chunk)

                # Send response chunks to chat
                for chunk in chunks:
                    connection.privmsg(self.channel, chunk)
                    self.logger.debug('Sending openAI response chunk: %s', chunk)

            else:
                response = 'Failed to generate response!'
                connection.privmsg(self.channel, response)
                self.logger.debug('Failed to send response: %s', response)

username = config.USERNAME
token = config.TOKEN # get this from https://twitchapps.com/tmi/
channel = config.USERNAME

# Create an instance of the bot and start it
bot = TwitchBot(username, token, channel)
bot.start()