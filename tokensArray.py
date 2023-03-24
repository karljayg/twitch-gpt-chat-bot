import spacy     #language small model of spacy
import nltk      #token libraries
from settings import config

# global variable
maxContextTokens = config.CONVERSATION_MAX_TOKENS
# initialize contextHistory array

# The contextHistory array is a list of tuples, where each tuple contains two elements: the message string and its corresponding token size. This allows us to keep track of both the message content and its size in the array.
# When a new message is added to the contextHistory array, its token size is determined using the nltk.word_tokenize() function. If the total number of tokens in the array exceeds the maxContextTokens threshold, the function starts deleting items from the end of the array until the total number of tokens is below the threshold.
# If the last item in the array has a token size less than or equal to the maxContextTokens threshold, the item is removed completely. However, if the last item has a token size greater than the threshold, the function removes tokens from the end of the message string until its token size is less than or equal to the threshold, and keeps the shortened message string in the array.
# If the total number of tokens in the array is still above the threshold after deleting the last item, the function repeats the process with the second-to-last item in the array, and continues deleting items until the total number of tokens is below the threshold.
# By using this logic, we can ensure that the contextHistory array always contains a maximum number of tokens specified by maxContextTokens, while keeping the most recent messages in the array.
# global contextHistory
# contextHistory = []

def add_new_msg(contextHistory, newMsg, logger):

    logger.debug("received newMsg: " + newMsg)

    # get token size of newMsg
    newMsgTokenSize = len(nltk.word_tokenize(newMsg))
    logger.debug("newMsgTokenSize: " + str(newMsgTokenSize))

    # add newMsg and its token size to the beginning of the array
    contextHistory.insert(0, (newMsg, newMsgTokenSize))

    # keep deleting items until total tokens is less than maxContextTokens
    totalTokens = sum([item[1] for item in contextHistory])
    while totalTokens > maxContextTokens:
        # get last item
        lastItem = contextHistory[-1]
        lastItemTokenSize = lastItem[1]
        # When the function needs to remove tokens from a message string to reduce its token size, it does so by removing tokens from the end of the string, token by token (or word by word).
        # For example, suppose the last message in the array has a token size of 150, and the maxContextTokens threshold is 100. To reduce the token size of the message to 100, the function would start by removing the last token of the message, then the second-to-last token, and so on, until the token size of the message is less than or equal to 100. This way, we can keep as much of the message content as possible while still ensuring that the total number of tokens in the array is below the threshold.
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
    #loading the english language small model of spacy
    en = spacy.load('en_core_web_sm')
    sw_spacy = en.Defaults.stop_words
    sw_spacy.remove('n’t','no','not','nothing','neither','never','almost','more','bottom','latter','three','fifteen','beside')
    sw_spacy.extend('besides')    
    words_list = words.split()
    words = [word for word in words_list if word.lower() not in sw_spacy]
    removed_words = [word for word in words_list if word.lower() in sw_spacy]
    new_text = " ".join(words)
    return new_text, removed_words
