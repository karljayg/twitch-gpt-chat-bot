import irc.bot
import requests
import logging
import openai
import re
from settings import config
import tokensArray
import asyncio
import random

# The contextHistory array is a list of tuples, where each tuple contains two elements: the message string and its corresponding token size. This allows us to keep track of both the message content and its size in the array.
# When a new message is added to the contextHistory array, its token size is determined using the nltk.word_tokenize() function. If the total number of tokens in the array exceeds the maxContextTokens threshold, the function starts deleting items from the end of the array until the total number of tokens is below the threshold.
# If the last item in the array has a token size less than or equal to the maxContextTokens threshold, the item is removed completely. However, if the last item has a token size greater than the threshold, the function removes tokens from the end of the message string until its token size is less than or equal to the threshold, and keeps the shortened message string in the array.
# If the total number of tokens in the array is still above the threshold after deleting the last item, the function repeats the process with the second-to-last item in the array, and continues deleting items until the total number of tokens is below the threshold.
# By using this logic, we can ensure that the contextHistory array always contains a maximum number of tokens specified by maxContextTokens, while keeping the most recent messages in the array.
global contextHistory
contextHistory = []

import sys
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

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
        self.ignore = config.IGNORE
        openai.api_key = config.OPENAI_API_KEY

        # Initialize the IRC bot
        irc.bot.SingleServerIRCBot.__init__(self, [(self.server, self.port, 'oauth:'+self.token)], self.username, self.username)

    #all msgs to channel are now logged
    def msgToChannel(self, message):
        self.connection.privmsg(self.channel, message)
        self.logger.debug("msg to channel: " + message)

    def processMessageForOpenAI(self, msg):
        #remove open sesame
        msg = msg.replace('open sesame', '')

        if bool(config.STOP_WORDS_FLAG):
            msg, removedWords = tokensArray.apply_stop_words_filter(msg)
            self.logger.debug("removed stop words: %s" , removedWords)

        #add User msg to conversation context
        tokensArray.add_new_msg(contextHistory, 'User: ' + msg + "\n", self.logger)

        #add complete array as msg to OpenAI
        msg = msg + tokensArray.get_printed_array("reversed", contextHistory)

        self.logger.debug("sent to OpenAI: %s" , msg)
        completion = openai.ChatCompletion.create(
            model=config.ENGINE,
            messages=[
                {"role": "user", "content": msg}
            ]
        )
        if completion.choices[0].message!=None:
            print(completion.choices[0].message.content)
            response = completion.choices[0].message.content

            #dont make it too obvious its a bot
            response = response.replace("As an AI language model, ", "")

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
                #remove all occurences of "AI: "
                chunk = re.sub(r'\bAI: ', '', chunk)
                self.msgToChannel(chunk)
                self.logger.debug('Sending openAI response chunk: %s', chunk)

                #add AI response to conversation context
                print("AI msg to chat: " + chunk)
                tokensArray.add_new_msg(contextHistory, 'AI: ' + chunk + "\n", self.logger)
                #print conversation so far
                print(tokensArray.get_printed_array("reversed", contextHistory))
        else:
            response = 'Failed to generate response!'
            self.msgToChannel(response)
            self.logger.debug('Failed to send response: %s', response)
  
    def on_welcome(self, connection, event):
        # Join the channel and say a greeting
        connection.join(self.channel)
        prefix="" #if any
        greeting_message = f'{prefix} {random.choice(config.BOT_GREETING_WORDS)}'
        self.msgToChannel(greeting_message)

    def on_pubmsg(self, connection, event):

        # Get message from chat
        msg = event.arguments[0].lower()
        sender = event.source.split('!')[0]
        #tags = {kvpair["key"]: kvpair["value"] for kvpair in event.tags}
        #user = {"name": tags["display-name"], "id": tags["user-id"]}

        #ignore certain users
        if sender.lower() in config.IGNORE:
            self.logger.debug("ignoring user: " + sender)
            return

        if config.PERSPECTIVE_DISABLED:
            toxicity_probability = 0
        else:
            toxicity_probability = tokensArray.get_toxicity_probability(msg, self.logger)
        #do not send toxic messages to openAI
        if toxicity_probability < config.TOXICITY_THRESHOLD:                                 

            # will only respond to a certain percentage of messages per config
            diceRoll=random.randint(0,100)/100
            self.logger.debug("rolled: " + str(diceRoll) + " settings: " + str(config.RESPONSE_PROBABILITY))        
            if diceRoll >= config.RESPONSE_PROBABILITY:
                self.logger.debug("will not respond")        
                return

            # any user greets via config keywords will be responded to
            if any(greeting in msg.lower() for greeting in config.GREETINGS_LIST_FROM_OTHERS):
                response = f"Hi {sender}!"
                self.msgToChannel(response)
                # return - sometimes it matches words so we want mathison to reply anyway

            if 'bye' in msg.lower():
                response = f"bye {sender}!"
                self.msgToChannel(response)
                return

            if 'gg' in msg.lower():
                response = f"HSWP"
                self.msgToChannel(response)
                return

            if 'bracket' in msg.lower() or '!b' in msg.lower() or 'FSL' in msg.upper() or 'fsl' in msg.lower():
                response = f"here is some info {config.BRACKET}"
                self.msgToChannel(response)
                return

            # Send response to direct msg or keyword which includes Mathison being mentioned
            if 'open sesame' in msg.lower() or any(sub in msg.lower() for sub in config.OPEN_SESAME_SUBSTITUTES):   
                self.processMessageForOpenAI(msg)
                return

            self.processMessageForOpenAI(msg)                    

        else:
            response = random.randint(1, 3)
            switcher = {
                1: f"{sender}, please refrain from sending toxic messages.",
                2: f"Woah {sender}! Strong language",
                3: f"Calm down {sender}. What's with the attitude?"
            }
            self.msgToChannel(switcher.get(response))  

username = config.USERNAME
token = config.TOKEN # get this from https://twitchapps.com/tmi/
channel = config.USERNAME

async def tasks_to_do():
    # Create an instance of the bot and start it
    bot = TwitchBot(username, token, channel)
    await bot.start()

async def main():
    tasks = []
    tasks.append(asyncio.create_task(tasks_to_do()))
    await asyncio.gather(tasks)

asyncio.run(main())