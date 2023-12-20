import random

from settings import config


def get_random_emote():
    emote_names = config.BOT_GREETING_EMOTES
    return f'{random.choice(emote_names)}'

def remove_emotes_from_message(message):
    for emote in config.BOT_GREETING_EMOTES:
        message = message.replace(emote, '')
    return message