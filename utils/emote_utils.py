import random

from settings import config


def get_random_emote():
    emote_names = config.BOT_GREETING_EMOTES
    return f'{random.choice(emote_names)}'
