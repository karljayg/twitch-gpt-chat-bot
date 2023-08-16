NAME = "Mathison"
VERSION = "0.1.0"
AUTHOR = "KJ Garcia"
AUTHOR_EMAIL = "kj@psistorm.com"
#  @karljayg on twitter/insta
#  more info: https://docs.google.com/document/d/1C8MM_BqbOYL9W0N0qu0T1g2DS7Uj_a6Vebd6LJLX4yU/edit?usp=sharing

"""
|   Twitch Settings
"""
# Twitch API credentials
CLIENT_ID = "psi_mathison"
TOKEN = ""
OWNER = "psi_mathison"
TRAINING_FILE = f"hypebot/training/twitchchatbot-gpt-ex-{NAME}-1"
PAGE = "kj_freeedom"
STREAMER_NICKNAME = "KJ"

# IRC Bot settings
HOST = "irc.chat.twitch.tv"
PORT = 6667
USERNAME = OWNER
CHANNEL = f"#{PAGE}"
URL = f"https://api.twitch.tv/kraken/users?login={USERNAME}"
HEADERS = {"Client-ID": CLIENT_ID, "Accept": "application/vnd.twitchtv.v5+json"}

"""
|   OpenAI Settings
"""
# OpenAI API credentials
OPENAI_API_KEY = "sk-"
OPENAI_DISABLED = False
ENGINE = "gpt-3.5-turbo"
TEMPERATURE = 0.99
MAX_TOKENS = 100
CONVERSATION_MAX_TOKENS = MAX_TOKENS
OUTPUT_PFX = ""

"""
|   SC2 Settings
"""
# StarCraft II settings
SC2_PLAYER_ACCOUNTS = ['myname']
REPLAYS_FOLDER = r"C:\Users\WHATEVER\OneDrive\Documents\StarCraft II\Accounts"
REPLAYS_FILE_EXTENSION = "SC2Replay"
ANALYZE_REPLAYS_FOR_TEST = True
REPLAY_TEST_FILE = ("test/replays/Gresvan LE (439).SC2Replay")
BUILD_ORDER_COUNT_TO_ANALYZE = 60
TEST_MODE = False  # will review SC2 game status JSON file in test instead of the SC2 client
IGNORE_REPLAYS = False  # will ignore game status when watching a replay
IGNORE_PREVIOUS_GAME_RESULTS_ON_FIRST_RUN = True  # will not comment on game status since its from last game before run
GAME_RESULT_TEST_FILE = "test/SC2_game_result_test.json"  # output of game result JSON file for analysis if needed
LAST_REPLAY_JSON_FILE = "temp/last_replay_data.json"  # json file of the last replay from sc2reader
LAST_REPLAY_SUMMARY_FILE = "temp/replay_summary.txt"  # summary file of build orders and units lost TODO: add other info

"""
|   Bot Behavior Settings
"""
IGNORE = ["psistorm_mathison", "psi_mathison", "Streamelements", "StreamElements"]  # users to ignore
RESPONSE_PROBABILITY = 0.7  # how often to respond? 1.0 = 100%  0.7 = 70%
MONITOR_GAME_SLEEP_SECONDS = 3  # sleep time between execution
GREETINGS_LIST_FROM_OTHERS = ['hi', 'HeyGuys', 'Hello']  # Mathison will say hi
OPEN_SESAME_SUBSTITUTES = "open sesame"  # override any delays/blocks and Mathison will respond
STOP_WORDS_FLAG = "adios amigo"  # remove/stop words - TODO: redo logic as it is off right now coz buggy
RESP_FREQUENCY = 1.0  # TODO: unused
RESP_WAIT = 5  # wait in seconds to respond TODO: review if this works
MAX_RESPONSIVENESS = 0.5  # TODO: unused

"""
|   Logging Settings
"""
LOG_FILE = "logs/bot.log"  # log file location

"""
|   Mood / Perspective Settings
"""

BOT_MOODS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]  # selected flavors of mood
BOT_PERSPECTIVES = [0, 1, 2, 3, 4, 5, 6, 7, 8]  # additional selected perspectives of response
PERSPECTIVE_INDEX_CUTOFF = 5  # if 4, the first 4 index are for replays: 0,1,2,3

# mood and perspectives options selected above (not to be confused with Google Perspective API
MOOD_OPTIONS = [
    "formal",  # 0 Use a more professional and refined tone in your instructions.
    "enthusiastic",  # 1 Show excitement and energy in your instructions.
    "confident",  # 2 Provide instructions with a strong and assured tone.
    "helpful",  # 3 Instruct in a supportive and assisting manner.
    "direct",  # 4 Provide clear and straightforward instructions without any extra frills.
    "playful",  # 5 Add a touch of playfulness and fun to your instructions.
    "authoritative",  # 6 Instruct with authority and decisiveness.
    "thoughtful",  # 7 Provide instructions with careful consideration and depth.
    "upbeat",  # 8 Maintain a positive and optimistic tone in your instructions.
    "empathetic",  # 9 Show understanding and empathy in your instructions.
    "curious",  # 10 Pose questions and instructions with a curious and inquisitive tone.
    "dry humor",
    # 11 Delivering statements with a subtle and understated sense of humor, often using irony or clever wordplay.
    "sarcastic",
    # 12 Using statements that express the opposite of what is actually meant, often with a sharp and mocking tone.
    "friendly",  # 13 Providing instructions in a warm and approachable manner, creating a sense of comfort and ease.
    "casual",  # 14 Instructing in a relaxed and informal way, as if having a laid-back conversation with a friend.
    "witty",
    # 15 Crafting instructions with clever and intelligent remarks, often using wordplay or clever insights
    # to engage effectively.
    "subtly funny",
    # 16 Incorporating light humor in a way that's not immediately obvious, adding a touch of amusement to your
    # instructions.
    "serious",
    # 17 Communicating with a focused and grave tone, indicating the importance and gravity of the instructions.
    "informative",  # 18 Delivering clear and factual instructions that provide valuable information and insights.
    "silly"  # 19 Expressing a lighthearted and humorous mood.
]

PERSPECTIVE_OPTIONS = [
    "talk about build order or units lost limit to 20 words in a poem",
    "find something interesting in the replay summary, limit to 15 words",
    "point out the most killed units for each player based on replay summary with joy, limit to 15 words",
    "look at the build order and anything interesting and write a haiku about it",
    "make a gamer joke about the game duration",
    # above are the first 5 for replay analysis, per PERSPECTIVE_INDEX_CUTOFF = 5
    "respond casually and concisely in only 15 words",
    "be extremely short in response, at most 16 words",
    "speak with expertise, at most 10 words",  # long winded, be careful
    "comment with excitement, max of 10 words",
    "add a small joke of 15 words or less",
    "end with a question of 15 words or less",
    "be very funny at the end",
    # Add other perspective options here
]

"""
|   Rarely changed Twitch Settings
"""

BOT_KJ_ALL_EMOTES = ['kjfreeLUL', 'kjfreeNOGG', 'kjfreePOG', 'kjfreePOGanimate', 'kjfreePSISTORM',
                     'kjfreePSISTORManimate', 'kjfreeSCUD', 'kjfreeFSL', 'kjfreeGG']  # emotes specific to channel
BOT_GREETING_EMOTES = ['4Head', '8-)', ':(', ':(', ':)', ':-(', ':-)', ':-/', ':-D', ':-O', ':-P', ':-Z', ':-\\', ':-o',
                       ':-p', ':-z', ':-|', ':/', ':/', ':D', ':D', ':O', ':O', ':P', ':P', ':Z', ':\\', ':o', ':p',
                       ':z', ':|', ':|', ';)', ';)', ';-)', ';-P', ';-p', ';P', ';P', ';p', '<3', '<3', '>(', '>(',
                       'ANELE', 'ArgieB8', 'ArsonNoSexy', 'AsexualPride', 'AsianGlow', 'B)', 'B)', 'B-)', 'BCWarrior',
                       'BOP', 'BabyRage', 'BatChest', 'BegWan', 'BibleThump', 'BigBrother', 'BigPhish', 'BisexualPride',
                       'BlackLivesMatter', 'BlargNaut', 'BloodTrail', 'BrainSlug', 'BrokeBack', 'BuddhaBar', 'CaitlynS',
                       'CarlSmile', 'ChefFrank', 'CoolCat', 'CoolStoryBob', 'CorgiDerp', 'CrreamAwk', 'CurseLit',
                       'DAESuppy', 'DBstyle', 'DansGame', 'DarkKnight', 'DarkMode', 'DatSheffy', 'DendiFace',
                       'DinoDance', 'DogFace', 'DoritosChip', 'DxCat', 'EarthDay', 'EleGiggle', 'EntropyWins',
                       'ExtraLife', 'FBBlock', 'FBCatch', 'FBChallenge', 'FBPass', 'FBPenalty', 'FBRun', 'FBSpiral',
                       'FBtouchdown', 'FUNgineer', 'FailFish', 'FallCry', 'FallHalp', 'FallWinning', 'FamilyMan',
                       'FootBall', 'FootGoal', 'FootYellow', 'FrankerZ', 'FreakinStinkin', 'FutureMan', 'GayPride',
                       'GenderFluidPride', 'Getcamped', 'GingerPower', 'GivePLZ', 'GlitchCat', 'GlitchLit', 'GlitchNRG',
                       'GrammarKing', 'GunRun', 'HSCheers', 'HSWP', 'HarleyWink', 'HassaanChop', 'HeyGuys',
                       'HolidayCookie', 'HolidayLog', 'HolidayPresent', 'HolidaySanta', 'HolidayTree', 'HotPokket',
                       'HungryPaimon', 'ImTyping', 'IntersexPride', 'InuyoFace', 'ItsBoshyTime', 'JKanStyle',
                       'Jebaited', 'Jebasted', 'JonCarnage', 'KAPOW', 'KEKHeim', 'Kappa', 'Kappa', 'KappaClaus',
                       'KappaPride', 'KappaRoss', 'KappaWealth', 'Kappu', 'Keepo', 'KevinTurtle', 'Kippa', 'KomodoHype',
                       'KonCha', 'Kreygasm', 'LUL', 'LaundryBasket', 'Lechonk', 'LesbianPride', 'LionOfYara', 'MVGame',
                       'Mau5', 'MaxLOL', 'MechaRobot', 'MercyWing1', 'MercyWing2', 'MikeHogu', 'MingLee', 'ModLove',
                       'MorphinTime', 'MrDestructoid', 'MyAvatar', 'NewRecord', 'NiceTry', 'NinjaGrumpy', 'NomNom',
                       'NonbinaryPride', 'NotATK', 'NotLikeThis', 'O.O', 'O.o', 'OSFrog', 'O_O', 'O_o', 'O_o',
                       'OhMyDog', 'OneHand', 'OpieOP', 'OptimizePrime', 'PJSalt', 'PJSugar', 'PMSTwin', 'PRChase',
                       'PanicVis', 'PansexualPride', 'PartyHat', 'PartyTime', 'PeoplesChamp', 'PermaSmug', 'PicoMause',
                       'PinkMercy', 'PipeHype', 'PixelBob', 'PizzaTime', 'PogBones', 'PogChamp', 'Poooound', 'PopCorn',
                       'PoroSad', 'PotFriend', 'PowerUpL', 'PowerUpR', 'PraiseIt', 'PrimeMe', 'PunOko', 'PunchTrees',
                       'R)', 'R)', 'R-)', 'RaccAttack', 'RalpherZ', 'RedCoat', 'ResidentSleeper', 'RitzMitz', 'RlyTho',
                       'RuleFive', 'RyuChamp', 'SMOrc', 'SSSsss', 'SUBprise', 'SabaPing', 'SeemsGood', 'SeriousSloth',
                       'ShadyLulu', 'ShazBotstix', 'Shush', 'SingsMic', 'SingsNote', 'SmoocherZ', 'SoBayed',
                       'SoonerLater', 'Squid1', 'Squid2', 'Squid3', 'Squid4', 'StinkyCheese', 'StinkyGlitch',
                       'StoneLightning', 'StrawBeary', 'SuperVinlin', 'SwiftRage', 'TBAngel', 'TF2John', 'TPFufun',
                       'TPcrunchyroll', 'TTours', 'TakeNRG', 'TearGlove', 'TehePelo', 'ThankEgg', 'TheIlluminati',
                       'TheRinger', 'TheTarFu', 'TheThing', 'ThunBeast', 'TinyFace', 'TombRaid', 'TooSpicy',
                       'TransgenderPride', 'TriHard', 'TwitchLit', 'TwitchRPG', 'TwitchSings', 'TwitchUnity',
                       'TwitchVotes', 'UWot', 'UnSane', 'UncleNox', 'VirtualHug', 'VoHiYo', 'VoteNay', 'VoteYea',
                       'WTRuck', 'WholeWheat', 'WhySoSerious', 'WutFace', 'YouDontSay', 'YouWHY', 'bleedPurple',
                       'cmonBruh', 'copyThis', 'duDudu', 'imGlitch', 'mcaT', 'o.O', 'o.o', 'o_O', 'o_o', 'panicBasket',
                       'pastaThat', 'riPepperonis', 'twitchRaid', 'kjfreeFSL', 'kjfreeGG']

"""
|   Google Perspective API Settings
"""
PERSPECTIVE_DISABLED = True
TOXICITY_THRESHOLD = 0.5
PERSPECTIVE_API_KEY = ''
PERSPECTIVE_URL = 'https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze?key='

# Other Integrations
ALIGULAC_API_KEY = ''
SC2REPLAY_STATS_AUTH_KEY = ""
SC2REPLAY_STATS_ACCOUNT_ID = ''  # if needed
SC2REPLAY_STATS_HASH = ""
SC2REPLAY_STATS_TOKEN = ""
SC2REPLAY_STATS_TIMESTAMP = ""

# Other settings
TOXIC_KEYWORDS = ["cussword"]
TOXIC_RESPONSE = "I'd respond to that but I don't think I should."
