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
# Emotes for bot greetings
BOT_GREETING_EMOTES = ['4Head', '8-)', ':(', ':(', ':)', ':-(', ':-)', ':-/', ':-D', ':-O', ':-P', ':-Z', ':-\\', ':-o', ':-p', ':-z', ':-|', ':/', ':/', ':D', ':D', ':O', ':O', ':P', ':P', ':Z', ':\\', ':o', ':p', ':z', ':|', ':|', ';)', ';)', ';-)', ';-P', ';-p', ';P', ';P', ';p', '<3', '<3', '>(', '>(', 'ANELE', 'ArgieB8', 'ArsonNoSexy', 'AsexualPride', 'AsianGlow', 'B)', 'B)', 'B-)', 'BCWarrior', 'BOP', 'BabyRage', 'BatChest', 'BegWan', 'BibleThump', 'BigBrother', 'BigPhish', 'BisexualPride', 'BlackLivesMatter', 'BlargNaut', 'BloodTrail', 'BrainSlug', 'BrokeBack', 'BuddhaBar', 'CaitlynS', 'CarlSmile', 'ChefFrank', 'CoolCat', 'CoolStoryBob', 'CorgiDerp', 'CrreamAwk', 'CurseLit', 'DAESuppy', 'DBstyle', 'DansGame', 'DarkKnight', 'DarkMode', 'DatSheffy', 'DendiFace', 'DinoDance', 'DogFace', 'DoritosChip', 'DxCat', 'EarthDay', 'EleGiggle', 'EntropyWins', 'ExtraLife', 'FBBlock', 'FBCatch', 'FBChallenge', 'FBPass', 'FBPenalty', 'FBRun', 'FBSpiral', 'FBtouchdown', 'FUNgineer', 'FailFish', 'FallCry', 'FallHalp', 'FallWinning', 'FamilyMan', 'FootBall', 'FootGoal', 'FootYellow', 'FrankerZ', 'FreakinStinkin', 'FutureMan', 'GayPride', 'GenderFluidPride', 'Getcamped', 'GingerPower', 'GivePLZ', 'GlitchCat', 'GlitchLit', 'GlitchNRG', 'GrammarKing', 'GunRun', 'HSCheers', 'HSWP', 'HarleyWink', 'HassaanChop', 'HeyGuys', 'HolidayCookie', 'HolidayLog', 'HolidayPresent', 'HolidaySanta', 'HolidayTree', 'HotPokket', 'HungryPaimon', 'ImTyping', 'IntersexPride', 'InuyoFace', 'ItsBoshyTime', 'JKanStyle', 'Jebaited', 'Jebasted', 'JonCarnage', 'KAPOW', 'KEKHeim', 'Kappa', 'Kappa', 'KappaClaus', 'KappaPride', 'KappaRoss', 'KappaWealth', 'Kappu', 'Keepo', 'KevinTurtle', 'Kippa', 'KomodoHype', 'KonCha', 'Kreygasm', 'LUL', 'LaundryBasket', 'Lechonk', 'LesbianPride', 'LionOfYara', 'MVGame', 'Mau5', 'MaxLOL', 'MechaRobot', 'MercyWing1', 'MercyWing2', 'MikeHogu', 'MingLee', 'ModLove', 'MorphinTime', 'MrDestructoid', 'MyAvatar', 'NewRecord', 'NiceTry', 'NinjaGrumpy', 'NomNom', 'NonbinaryPride', 'NotATK', 'NotLikeThis', 'O.O', 'O.o', 'OSFrog', 'O_O', 'O_o', 'O_o', 'OhMyDog', 'OneHand', 'OpieOP', 'OptimizePrime', 'PJSalt', 'PJSugar', 'PMSTwin', 'PRChase', 'PanicVis', 'PansexualPride', 'PartyHat', 'PartyTime', 'PeoplesChamp', 'PermaSmug', 'PicoMause', 'PinkMercy', 'PipeHype', 'PixelBob', 'PizzaTime', 'PogBones', 'PogChamp', 'Poooound', 'PopCorn', 'PoroSad', 'PotFriend', 'PowerUpL', 'PowerUpR', 'PraiseIt', 'PrimeMe', 'PunOko', 'PunchTrees', 'R)', 'R)', 'R-)', 'RaccAttack', 'RalpherZ', 'RedCoat', 'ResidentSleeper', 'RitzMitz', 'RlyTho', 'RuleFive', 'RyuChamp', 'SMOrc', 'SSSsss', 'SUBprise', 'SabaPing', 'SeemsGood', 'SeriousSloth', 'ShadyLulu', 'ShazBotstix', 'Shush', 'SingsMic', 'SingsNote', 'SmoocherZ', 'SoBayed', 'SoonerLater', 'Squid1', 'Squid2', 'Squid3', 'Squid4', 'StinkyCheese', 'StinkyGlitch', 'StoneLightning', 'StrawBeary', 'SuperVinlin', 'SwiftRage', 'TBAngel', 'TF2John', 'TPFufun', 'TPcrunchyroll', 'TTours', 'TakeNRG', 'TearGlove', 'TehePelo', 'ThankEgg', 'TheIlluminati', 'TheRinger', 'TheTarFu', 'TheThing', 'ThunBeast', 'TinyFace', 'TombRaid', 'TooSpicy', 'TransgenderPride', 'TriHard', 'TwitchLit', 'TwitchRPG', 'TwitchSings', 'TwitchUnity', 'TwitchVotes', 'UWot', 'UnSane', 'UncleNox', 'VirtualHug', 'VoHiYo', 'VoteNay', 'VoteYea', 'WTRuck', 'WholeWheat', 'WhySoSerious', 'WutFace', 'YouDontSay', 'YouWHY', 'bleedPurple', 'cmonBruh', 'copyThis', 'duDudu', 'imGlitch', 'mcaT', 'o.O', 'o.o', 'o_O', 'o_o', 'panicBasket', 'pastaThat', 'riPepperonis', 'twitchRaid', 'kjfreeFSL', 'kjfreeGG']
BOT_KJ_ALL_EMOTES = ['kjfreeLUL', 'kjfreeNOGG', 'kjfreePOG', 'kjfreePOGanimate', 'kjfreePSISTORM', 'kjfreePSISTORManimate', 'kjfreeSCUD', 'kjfreeFSL', 'kjfreeGG']
BOT_KJ_FOLLOWER_EMOTES = ['kjfreeLUL', 'kjfreeNOGG', 'kjfreePOG', 'kjfreePOGanimate', 'kjfreePSISTORM', 'kjfreePSISTORManimate', 'kjfreeSCUD', 'kjfreeFSL', 'kjfreeGG']

#streamer SC2 account
SC2_PLAYER_ACCOUNTS = ['myname']
PLAY_ON_REPLAY = True

GREETINGS_LIST_FROM_OTHERS = ['hi', 'HeyGuys', 'Hello']
OPEN_SESAME_SUBSTITUTES = "open sesame"
STOP_WORDS_FLAG = "adios amigo"

#PERSPECTIVE API SETTINGS
"""
"TOXICITY THRESHOLD - decimal value, between 0.0 to 1.0 determines the toxicity level allowed to pass through Perspective's filters.
"PERSPECTIVE_API_KEY - string value, unique identifier required to access Perspective API.
"PERSPECTIVE_URL - 
"""
PERSPECTIVE_DISABLED = True
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
