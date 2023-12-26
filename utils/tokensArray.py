import json
import requests
import spacy  # language small model of spacy
import nltk  # token libraries
from settings import config
import nltk
import tiktoken

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# global variable
maxContextTokens = config.CONVERSATION_MAX_TOKENS
# initialize contextHistory array

# The contextHistory array is a list of tuples, where each tuple contains two elements: the message string and its
# corresponding token size. This allows us to keep track of both the message content and its size in the array.
# For example, suppose the contextHistory array contains the following messages:
# [
#     ("Hi, how are you?", 4),
#     ("I'm good, thanks!", 4),
#     ("What are you up to?", 5),
#     ("I'm just working on my homework.", 7),
#     ("Cool, I'm just watching TV.", 6),
#     ("Nice. What show are you watching?", 6)
# ]
# The first element in each tuple is the message string, and the second element is its token size. In this example,
# the total number of tokens in the array is 32 (4 + 4 + 5 + 7 + 6 + 6). If the maxContextTokens threshold is 30,
# the add_new_msg() function will remove items from the end of the array until the total number of tokens is below
# the threshold. In this case, it will remove the last two items in the array, leaving the following messages:
# [
#     ("Hi, how are you?", 4),
#     ("I'm good, thanks!", 4),
#     ("What are you up to?", 5),
#     ("I'm just working on my homework.", 7)
# ]
# The total number of tokens in the array is now 20 (4 + 4 + 5 + 7),
# which is below the maxContextTokens threshold of 30.
# The add_new_msg() function is called whenever a new message is received.
# It takes two arguments: the contextHistory array, and the new message string.
# The function adds the new message string to the beginning of the array, along with its token size.
# It then checks the total number of tokens in the array. If the total number of tokens is below the
# maxContextTokens threshold, the function does nothing. If the total number of tokens is above the threshold,
# the function starts removing items from the end of the array until the total number of tokens is below the threshold.
# For example, suppose the contextHistory array contains the following messages:
# [
#     ("Hi, how are you?", 4),
#     ("I'm good, thanks!", 4),
#     ("What are you up to?", 5),
#     ("I'm just working on my homework.", 7),
#     ("Cool, I'm just watching TV.", 6),
#     ("Nice. What
# When a new message is added to the contextHistory array, its token size is determined using the
# nltk.word_tokenize() function. If the total number of tokens in the array exceeds the maxContextTokens threshold,
# the function starts deleting items from the end of the array until the total number of tokens is below the threshold.
# If the last item in the array has a token size less than or equal to the maxContextTokens threshold, the item is
# removed completely. However, if the last item has a token size greater than the threshold, the function removes
# tokens from the end of the message string until its token size is less than or equal to the threshold, and keeps
# the shortened message string in the array.
# If the total number of tokens in the array is still above the threshold after deleting the last item, the function
# repeats the process with the second-to-last item in the array, and continues deleting items until the total number
# of tokens is below the threshold.
# By using this logic, we can ensure that the contextHistory array always contains a maximum number of tokens
# specified by maxContextTokens, while keeping the most recent messages in the array.
# global contextHistory
# contextHistory = []


def get_toxicity_probability(message, logger):
    logger.debug("checking toxicity score.")
    # api_key = config.PERSPECTIVE_API_KEY
    # url = "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze?key=" + api_key
    url = config.PERSPECTIVE_URL + config.PERSPECTIVE_API_KEY
    headers = {'Content-Type': 'application/json'}
    data = {
        'comment': {'text': message},
        'languages': ['en'],
        'requestedAttributes': {'TOXICITY': {}},
        'doNotStore': True
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    response_dict = json.loads(response.content)
    if 'attributeScores' in response_dict:
        toxicity_score = response_dict['attributeScores']['TOXICITY']['summaryScore']['value']
        logger.debug("toxicity score: " + str(toxicity_score))
        return toxicity_score
    else:
        logger.debug("no toxicity score received")
        return None


# Example usage
# toxicity_score = get_toxicity_probability("You're an idiot.")
# print("Toxicity probability:", toxicity_score)

def add_new_msg(contextHistory, newMsg, logger):
    logger.debug("received newMsg: " + newMsg)

    # get token size of newMsg
    newMsgTokenSize = num_tokens_from_string(newMsg, "cl100k_base")
    logger.debug("newMsgTokenSize: " + str(newMsgTokenSize))

    # add newMsg and its token size to the beginning of the array
    contextHistory.insert(0, (newMsg, newMsgTokenSize))

    # keep deleting items until total tokens is less than maxContextTokens
    totalTokens = sum([item[1] for item in contextHistory])
    logger.debug("totalTokens: " + str(totalTokens))
    while totalTokens > maxContextTokens:
        # get last item
        lastItem = contextHistory[-1]
        lastItemTokenSize = lastItem[1]
        # When the function needs to remove tokens from a message string to reduce its token size, it does so
        # by removing tokens from the end of the string, token by token (or word by word).
        # For example, suppose the last message in the array has a token size of 150, and the maxContextTokens
        # threshold is 100. To reduce the token size of the message to 100, the function would start by removing
        # the last token of the message, then the second-to-last token, and so on, until the token size of the
        # message is less than or equal to 100. This way, we can keep as much of the message content as possible
        # while still ensuring that the total number of tokens in the array is below the threshold.
        if lastItemTokenSize <= maxContextTokens:
            # if last item can be removed completely, remove it
            contextHistory.pop()
        else:
            # otherwise, remove tokens from last item and keep its string
            lastItemString = lastItem[0]
            lastItemTokens = nltk.word_tokenize(lastItemString)
            newLastItemTokens = lastItemTokens[:-lastItemTokenSize]
            newLastItemString = ' '.join(newLastItemTokens)
            contextHistory[-1] = (newLastItemString, len(newLastItemTokens))
        totalTokens = sum([item[1] for item in contextHistory])
        logger.debug("reduced totalTokens: " + str(totalTokens))


def get_printed_array(order, contextHistory):
    arrayString = ""
    if order == "reversed":
        for item in reversed(contextHistory):
            arrayString = arrayString + item[0]
    else:
        for item in contextHistory:
            arrayString = arrayString + item[0]
    return arrayString

def apply_stop_words_filter(words):
    removed_words = []
    # loading the english language small model of spacy
    en = spacy.load('en_core_web_sm')
    sw_spacy = en.Defaults.stop_words

    words_to_remove = ['n’t', 'no', 'not', 'nothing', 'neither', 'never', 'almost', 'more', 'bottom', 'latter', 'three',
                       'fifteen', 'beside']
    for word in words_to_remove:
        sw_spacy.discard(word)

    sw_spacy.update(['besides'])

    words_list = words.split()
    words = [word for word in words_list if word.lower() not in sw_spacy]
    removed_words = [word for word in words_list if word.lower() in sw_spacy]
    new_text = " ".join(words)
    return new_text, removed_words

def replace_non_ascii(s, replacement='?'):
    return "".join(c if ord(c) < 128 else replacement for c in s)

def truncate_to_byte_limit(input_string, byte_limit):
    encoded_string = input_string.encode('utf-8')
    current_byte_total = len(encoded_string)

    if current_byte_total <= byte_limit:
        print(f"Current byte total: {current_byte_total} bytes (within limit)")
        return input_string
    else:
        truncated_string = encoded_string[:byte_limit].decode('utf-8', 'ignore').rstrip()
        new_byte_total = len(truncated_string.encode('utf-8'))
        print(f"Current byte total: {current_byte_total} bytes, truncated to {new_byte_total} bytes")
        return truncated_string

def num_tokens_from_string(string: str, encoding_name: str) -> int:
    # Returns the number of tokens in a text string depending on tokenizer used
    encoding = tiktoken.get_encoding(encoding_name)
    if (config.TOKENIZER == "tiktoken"):
        num_tokens = len(encoding.encode(string))
    else:
        num_tokens = len(nltk.word_tokenize(str))

    return num_tokens