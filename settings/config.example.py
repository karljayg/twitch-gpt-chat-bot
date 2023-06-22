"""
|   Twitch Settings
"""
NAME = "Twitchchatbot GPT"
OWNER = ""
CLIENT_ID = ""
TOKEN = ""
TRAINING_FILE = f"hypebot/training/twitchchatbot-gpt-ex-{NAME}-1"
PAGE = ""

HOST = "irc.chat.twitch.tv"
PORT = 6667
USERNAME = OWNER

#IRC Bot variables
URL = f"https://api.twitch.tv/kraken/users?login={USERNAME}"
HEADERS = {"Client-ID": CLIENT_ID, "Accept":"application/vnd.twitchtv.v5+json"}

CHANNEL = f"#{PAGE}"

#OPENAI SETTINGS
OPENAI_API_KEY = ""
#ENGINE="davinci"
ENGINE="gpt-3.5-turbo" #aka MODEL
TEMPERATURE=0.99
MAX_TOKENS=100
CONVERSATION_MAX_TOKENS=MAX_TOKENS
OUTPUT_PFX=""

"""
"RESP_FREQUENCY- decimal value, between 0.0 to 1.0 determines the toxicity level allowed to pass through Perspective's filters.
"RESP_WAIT - integer value, determines how many seconds before the message from OpenAI will be displayed in the twitch channel.
"MAX_RESPONSIVENESS - DECIMAL representation of max percentage of responses vs participant count ratio per chat cycle that the chatbot it allowed to make in total.
"RESPONSE_PROBABILITY - DECIMAL representation of desired probability of chatbot to respond to any message it receives while not yet reaching its MAX_RESPONSIVENESS.
"""
RESP_FREQUENCY = 1.0
RESP_WAIT = 5
MAX_RESPONSIVENESS = 0.5
RESPONSE_PROBABILITY = 0.7

#LOG SETTINGS
LOG_FILE = "bot.log"

#missing config items - need to clean up
BOT_GREETING_WORDS = "hello"
GREETINGS_LIST_FROM_OTHERS = "hi"
OPEN_SESAME_SUBSTITUTES = "open sesame"

#PERSPECTIVE API SETTINGS
"""
"TOXICITY THRESHOLD - decimal value, between 0.0 to 1.0 determines the toxicity level allowed to pass through Perspective's filters.
"PERSPECTIVE_API_KEY - string value, unique identifier required to access Perspective API.
"PERSPECTIVE_URL - 
"""
TOXICITY_THRESHOLD = 0.5
PERSPECTIVE_API_KEY = ''
PERSPECTIVE_URL = 'https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze?key='

"""
"IGNORE - an array of strings that will hold the names of the users you want the bot to ignore. P.S.: this is case sensitive
"""
IGNORE = ["psistorm_mathison", "KJ_Freeedom", "Streamelements"]

"""
"TOXIC_KEYWORDS - an array of strings that holds bad words
"TOXIC_RESPONSE - a string that will be used to reply to a user if the bot responds with a toxic comment
"""
TOXIC_KEYWORDS = ["fuck", "shit", "ass", "bullshit"]
TOXIC_RESPONSE = "I'd respond to that but I don't think I should."
