NAME = "Mathison"
VERSION = "0.1.0"
AUTHOR = "KJ Garcia"
AUTHOR_EMAIL = "kj@psistorm.com"
#  @karljayg on twitter/insta
#  more info: https://docs.google.com/document/d/1C8MM_BqbOYL9W0N0qu0T1g2DS7Uj_a6Vebd6LJLX4yU/edit?usp=sharing
BOT_COMMANDS = """
 wiki <question>,
 career <player>,
 history <player>,
 head to head <player1> <player2>,
 games in <hrs> hours - limit 72,
 open sesame - ignored users will be responded to
"""

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
HEADERS = {"Client-ID": CLIENT_ID,
           "Accept": "application/vnd.twitchtv.v5+json"}
TWITCH_CHAT_BYTE_LIMIT = 450 #512 but to account for overhead

"""
|   Discord Settings
"""
# Discord Bot settings
DISCORD_TOKEN = ""  # Your Discord bot token
DISCORD_CHANNEL_ID = None  # Channel ID (integer) where the bot should operate
DISCORD_ENABLED = True  # Set to False to disable Discord bot

# Discord Behavior Settings
DISCORD_RESPOND_TO_MENTIONS = True  # Reply when @psi_mathison is mentioned
DISCORD_RESPOND_TO_REPLIES = True  # Reply when someone replies to bot's messages
DISCORD_DICE_RESPONSE_PROBABILITY = 0.35  # Half of RESPONSE_PROBABILITY for dice roll responses
DISCORD_LAST_WORD_ENABLED = True  # Reply to messages with no replies after timeout (improved: only replies to most recent)
DISCORD_LAST_WORD_TIMEOUT_HOURS = 3  # Hours to wait before replying to unreplied messages
DISCORD_LAST_WORD_CHECK_FREQUENCY_HOURS = 1  # How often to check for unreplied messages (recommended: 0.5-2 hours)

"""
|   OpenAI Settings
"""
# OpenAI API credentials
OPENAI_API_KEY = "sk-"
OPENAI_DISABLED = False
ENGINE = "gpt-3.5-turbo"
TEMPERATURE = 0.99
MAX_TOKENS = 3200  # actual max for chatgpt 3.5 turbo is 4096, minus overhead
CONVERSATION_MAX_TOKENS = 3000  # max just for the conversation
OUTPUT_PFX = ""
TOKENIZER = "tiktoken"  # tiktoken or nltk supported
TOKENIZER_ENCODING = "cl100k_base"  # cl100k_base

"""
|   DB Settings
"""
DB_HOST = "localhost"
DB_USER = ""
DB_PASSWORD = ""
DB_NAME = "mathison"
HEARTBEAT_MYSQL = 20 # iterations, usually GAME_DURATION_SECONDS / MONITOR_GAME_SLEEP_SECONDS * this number

"""
|   SC2 Settings
"""
# StarCraft II settings
SC2_PLAYER_ACCOUNTS = ['myname']
SC2_BARCODE_ACCOUNTS = ['II','III','IIII','IIIII','IIIIII','IIIIIII','IlIlIl','IlIlIlIl','IlIlIlIlIl','IlIlIlIlIlIl','IlIlIlIlIlIlIl','IlIlIlIlIlIlIlIl']
SC2_COMPUTER_ACCOUNTS = ['A.I. 1 (Elite)','A.I. 1 (Very Easy)','A.I. 1 (Easy)','A.I. 1 (Medium)','A.I. 1 (Hard)','A.I. 1 (Harder)','A.I. 1 (Very Hard)']
REPLAYS_FOLDER = r"C:\Users\WHATEVER\OneDrive\Documents\StarCraft II\Accounts"
REPLAYS_FILE_EXTENSION = "SC2Replay"

# goes together, turn off to not get confused
USE_CONFIG_TEST_REPLAY_FILE = False
REPLAY_TEST_FILE = ("test/replays/Royal Blood LE (428).SC2Replay")

BUILD_ORDER_COUNT_TO_ANALYZE = 60
# games less than this seconds will be considered abandoned for better commentary
ABANDONED_GAME_THRESHOLD = 15
# TODO: make this more intuitive and less confusing, as test modes are different from running replays period
TEST_MODE = True  # misc. tests, like with DB and other items
# will review SC2 game status JSON file in test instead of the SC2 client
TEST_MODE_SC2_CLIENT_JSON = False
# will ignore game status when watching a replay
IGNORE_GAME_STATUS_WHILE_WATCHING_REPLAYS = False
# will not comment on game status since its from last game before run
IGNORE_PREVIOUS_GAME_RESULTS_ON_FIRST_RUN = True
# output of game result JSON file for analysis if needed
GAME_RESULT_TEST_FILE = "test/SC2_game_result_test.json"
# json file of the last replay from sc2reader
LAST_REPLAY_JSON_FILE = "temp/last_replay_data.json"
# summary file of build orders and units lost TODO: add other info
LAST_REPLAY_SUMMARY_FILE = "temp/replay_summary.txt"

PLAYER_INTROS_ENABLED = True  # enabled playing mp3 files of player intros
SOUNDS_CONFIG_FILE = 'settings/SC2_sounds.json'

"""
|   Bot Behavior Settings
"""
IGNORE = ["psistorm_mathison", "psi_mathison",
          "Streamelements", "StreamElements"]  # users to ignore
RESPONSE_PROBABILITY = 0.7  # how often to respond? 1.0 = 100%  0.7 = 70%
# sleep time between execution, any less than 7 risks new replay not done yet
MONITOR_GAME_SLEEP_SECONDS = 7
GREETINGS_LIST_FROM_OTHERS = ['hi', 'HeyGuys', 'Hello']  # Mathison will say hi
# override any delays/blocks and Mathison will respond
OPEN_SESAME_SUBSTITUTES = "open sesame"
# remove/stop words - TODO: redo logic as it is off right now coz buggy
STOP_WORDS_FLAG = "adios amigo"
RESP_FREQUENCY = 1.0  # TODO: unused
RESP_WAIT = 5  # wait in seconds to respond TODO: review if this works
MAX_RESPONSIVENESS = 0.5  # TODO: unused

"""
|   Audio Settings
"""
# Master switch for all audio features - disable for server deployments
ENABLE_AUDIO = True

# Text-to-Speech settings
TEXT_TO_SPEECH = True  # Enable TTS for bot responses

# Speech-to-Text settings  
ENABLE_SPEECH_TO_TEXT = True  # Enable voice command recognition
USE_WHISPER = False  # Use OpenAI Whisper for speech2text, or normal python library speechrecognition

# Game Sound settings
ENABLE_GAME_SOUNDS = True  # Enable SC2 game event sounds (win/loss/start/etc)

# StarCraft II Monitoring settings
ENABLE_SC2_MONITORING = True  # Enable SC2 client monitoring for game events (disable for server deployments)

# FSL Integration Settings
ENABLE_FSL_INTEGRATION = True  # Enable FSL reviewer link integration
FSL_API_URL = "http://localhost/psistorm.com/fsl/api/service.php"
FSL_API_TOKEN = "fsl_api_7x9k2m4n8p3q6r9s2t5v8w1y4z7a0c3f6h9j2m5p8s1v4y7"
FSL_REVIEWER_WEIGHT = 1.0  # Default weight for Twitch viewers

# Pattern Learning System Settings
ENABLE_PATTERN_LEARNING = True  # Enable SC2 build pattern learning from player comments
PLAYER_COMMENT_TIMEOUT_SECONDS = 60  # Timeout for player comment input (in seconds)
PATTERN_LEARNING_DELAY_SECONDS = 3  # Delay before prompting for player comments (wait for replay processing)
PATTERN_LEARNING_SIMILARITY_THRESHOLD = 0.7  # Minimum similarity score to consider patterns matching
PATTERN_LEARNING_MAX_PATTERNS = 1000  # Maximum number of patterns to store in memory
PATTERN_DATA_DIR = "data"  # Directory to store learned patterns
PATTERN_LEARNING_PROMPT_FOR_COMMENTS = True  # Set to True to always prompt for player comments (never auto-process)

# ML Opponent Analysis Settings
ENABLE_ML_OPPONENT_ANALYSIS = True  # Enable ML analysis of opponents at game start
ML_ANALYSIS_SIMILARITY_THRESHOLD = 0.05  # Minimum similarity score (5%) to suggest ML analysis
ML_ANALYSIS_STRATEGIC_BONUS = 0.1  # 10% bonus per strategic keyword match
ML_ANALYSIS_COMMENT_EXACT_MATCH_BONUS = 1.0  # 100% bonus for exact comment matches
ML_ANALYSIS_COMMENT_KEYWORD_BONUS = 0.5  # 50% bonus for keyword overlap with opponent comments
ML_ANALYSIS_COMMENT_REVERSE_BONUS = 0.3  # 30% bonus for reverse keyword matches

# Pattern Learning Suggestion Threshold
# This controls when the system suggests a pattern match after a game.
# The system uses build-to-build comparison (opponent's strategic items, timing, order).
# Based on validation testing across 368 games with 10 strategy groups:
#   - Similar strategies match at 70-93% (avg 73.9%)
#   - Exact same builds match at 85-100%
#   - Different strategies score <60%
# Recommended values:
#   - 0.60 (60%): Balanced - catches most strategies, filters noise
#   - 0.70 (70%): Stricter - high confidence only, may miss some edge cases
#   - 0.35 (35%): Permissive - catches weak matches, risk of false positives
PATTERN_SUGGESTION_MIN_SIMILARITY = 0.60

# Race-specific strategic items to look for in opponent build orders
# Used when analyzing opponent builds to identify key tech paths and strategies
SC2_STRATEGIC_ITEMS = {
    'Zerg': {
        'buildings': 'SpawningPool, RoachWarren, BanelingNest, Spire, GreaterSpire, NydusNetwork, NydusWorm, HydraliskDen, InfestationPit, UltraliskCavern, LurkerDen, EvolutionChamber, SpineCrawler, SporeCrawler',
        'units': 'Zergling, Roach, Baneling, Mutalisk, Lurker, Hydralisk, Broodlord, SwarmHost, Viper, Infestor, Ultralisk, Corruptor, Ravager',
        'upgrades': 'Metabolic Boost, Adrenal Glands, Pneumatized Carapace, Glial Reconstitution, Burrow, Tunneling Claws, Grooved Spines, Muscular Augments, Zerg Melee Attacks, Zerg Missile Attacks, Zerg Ground Carapace'
    },
    'Terran': {
        'buildings': 'Starport, FusionCore, Factory, GhostAcademy, Armory, TechLab, Reactor, EngineeringBay, Bunker, MissileTurret, SensorTower, PlanetaryFortress',
        'units': 'Ghost, Cyclone, Liberator, Banshee, Battlecruiser, Widow Mine, Raven, Hellion, Hellbat, Siege Tank, Thor, Marauder, Reaper, Viking, Medivac',
        'upgrades': 'Stimpack, Combat Shields, Concussive Shells, Siege Tech, Drilling Claws, Smart Servos, Banshee Cloak, Terran Infantry Weapons, Terran Infantry Armor, Terran Vehicle Weapons, Terran Vehicle Plating, Terran Ship Weapons, Terran Ship Plating, Hi-Sec Auto Tracking, Hyperflight Rotors, Mag-Field Accelerator'
    },
    'Protoss': {
        'buildings': 'Forge, TwilightCouncil, DarkShrine, Stargate, RoboticsFacility, TemplarArchive, FleetBeacon, RoboticsBay, PhotonCannon, ShieldBattery',
        'units': 'Dark Templar, Immortal, Void Ray, Oracle, Phoenix, Colossus, Disruptor, Tempest, Carrier, High Templar, Archon, Adept, Sentry, Stalker, Warp Prism, Observer',
        'upgrades': 'Charge, Blink, Resonating Glaives, Extended Thermal Lance, Protoss Ground Weapons, Protoss Ground Armor, Protoss Air Weapons, Protoss Air Armor, Protoss Shields'
    }
}


"""
|   Logging Settings
"""
LOG_FILE = "logs/bot.log"  # log file location

"""
|   Mood / Perspective Settings
"""

BOT_MOODS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13,
             14, 15, 16, 17, 18, 19]  # selected flavors of mood
# additional selected perspectives of response
BOT_PERSPECTIVES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
PERSPECTIVE_INDEX_CUTOFF = 7  # if 4, the first 4 index are for replays: 0,1,2,3

# mood and perspectives options selected above (not to be confused with Google Perspective API
MOOD_OPTIONS = [
    # 0 Use a more professional and refined tone in your instructions.
    "formal",
    "enthusiastic",  # 1 Show excitement and energy in your instructions.
    "confident",  # 2 Provide instructions with a strong and assured tone.
    "helpful",  # 3 Instruct in a supportive and assisting manner.
    # 4 Provide clear and straightforward instructions without any extra frills.
    "direct",
    "playful",  # 5 Add a touch of playfulness and fun to your instructions.
    "authoritative",  # 6 Instruct with authority and decisiveness.
    # 7 Provide instructions with careful consideration and depth.
    "thoughtful",
    # 8 Maintain a positive and optimistic tone in your instructions.
    "upbeat",
    "empathetic",  # 9 Show understanding and empathy in your instructions.
    # 10 Pose questions and instructions with a curious and inquisitive tone.
    "curious",
    "dry humor",
    # 11 Delivering statements with a subtle and understated sense of humor, often using irony or clever wordplay.
    "sarcastic",
    # 12 Using statements that express the opposite of what is actually meant, often with a sharp and mocking tone.
    # 13 Providing instructions in a warm and approachable manner, creating a sense of comfort and ease.
    "friendly",
    # 14 Instructing in a relaxed and informal way, as if having a laid-back conversation with a friend.
    "casual",
    "witty",
    # 15 Crafting instructions with clever and intelligent remarks, often using wordplay or clever insights
    # to engage effectively.
    "subtly funny",
    # 16 Incorporating light humor in a way that's not immediately obvious, adding a touch of amusement to your
    # instructions.
    "serious",
    # 17 Communicating with a focused and grave tone, indicating the importance and gravity of the instructions.
    # 18 Delivering clear and factual instructions that provide valuable information and insights.
    "informative",
    "silly"  # 19 Expressing a lighthearted and humorous mood.
]

# PERSPECTIVE_OPTIONS for AI responses
# Note: The first 7 options (index 0-6) are used for replay analysis
# All replay analysis prompts include anti-hallucination instructions to use ONLY the Winners/Losers data provided
PERSPECTIVE_OPTIONS = [
    "talk about build order or units lost in a very short poem of 20 words or less. If mentioning game results, use only the Winners/Losers data provided.",
    "identify and name the hero unit from 'Units Lost by' section (e.g. 'Void Ray', 'Siege Tank'), mention its count if shown, limit to 12 words",
    "pick a specific strategic detail from build order or units lost (mention actual unit names/buildings/numbers), limit to 18 words",
    "mention specific unit types and counts from 'Units Lost by' section (e.g. '183 drones vs 43'), highlight biggest differences, limit to 20 words",
    "write game summary in haiku using specific units and even the map name, limit to 25 words. Include who won/lost based on the Winners/Losers data.",
    "Based on the EXACT game results shown (Winners/Losers), mention the game duration minutes, and make a gamer joke about it, keeping in mind average game time is 15 minutes. Use ONLY the Winners/Losers data provided - do NOT make assumptions about who won.",
    "do a friendly roast using ONLY actual specific units/buildings/numbers from THIS GAME's build order or units lost data provided, limit to 25 words. DO NOT invent units not in the data. Remember who actually won/lost from the Winners/Losers data.",
    # above are the first 7 for replay analysis (index 0-6), per PERSPECTIVE_INDEX_CUTOFF = 7
    # All replay analysis prompts include anti-hallucination instructions to prevent AI from making up wrong winners/losers
    "respond casually and concisely in only 15 words",
    "be extremely short in response, at most 16 words",
    "speak with expertise, at most 10 words",  # long winded, be careful
    "comment with excitement, max of 10 words",
    "add a small joke of 15 words or less",
    "end with a question of 15 words or less",
    "be very funny at the end, limit to 15 words",
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

# Unit/Building/Upgrade Abbreviations for Twitch Chat
# Used to make build orders more readable by replacing full names with common slang
UNIT_ABBREVIATIONS = {
    # TERRAN
    'Siege Tank': 'Tank',
    'Battlecruiser': 'BC',
    'Widow Mine': 'Mine',
    'CommandCenter': 'CC',
    'Orbital Command': 'Orbital',
    'SupplyDepot': 'Depot',
    'Barracks': 'Rax',
    'BarracksReactor': 'Rax Reactor',
    'BarracksTechLab': 'Rax Tech',
    'Factory': 'Fact',
    'FactoryTechLab': 'Fact Tech',
    'Refinery': 'Gas',
    'EngineeringBay': 'Ebay',
    'MissileTurret': 'Turret',
    
    # PROTOSS
    'Dark Templar': 'DT',
    'Void Ray': 'VoidRay',
    'Warp Prism': 'Prism',
    'Observer': 'Obs',
    'Assimilator': 'Gas',
    'Gateway': 'Gate',
    'CyberneticsCore': 'Cyber',
    'PhotonCannon': 'Cannon',
    'ShieldBattery': 'Battery',
    'TwilightCouncil': 'Twilight',
    'Stargate': 'SG',
    'RoboticsFacility': 'Robo',
    'RoboticsBay': 'Robo Bay',
    'FleetBeacon': 'Fleet',
    'Extended Thermal Lance': 'Range',
    
    # ZERG
    'Zergling': 'Ling',
    'Baneling': 'Bane',
    'Hydralisk': 'Hydra',
    'Mutalisk': 'Muta',
    'Ultralisk': 'Ultra',
    'Overlord': 'OL',
    'Hatchery': 'Hatch',
    'Extractor': 'Gas',
    'SpawningPool': 'Pool',
    'BanelingNest': 'Bane Nest',
    'RoachWarren': 'Roach Warren',
    'HydraliskDen': 'Hydra Den',
    'SpineCrawler': 'Spine',
    'SporeCrawler': 'Spore',
    'EvolutionChamber': 'Evo',
    'Metabolic Boost': 'Ling Speed',
}
