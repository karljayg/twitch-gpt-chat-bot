import pyttsx3
import logging
import time
from settings import config

logging.basicConfig(level=logging.INFO)
logging.getLogger('comtypes').setLevel(logging.INFO)

def speak_text(text, mode=1):
    # Initialize the converter
    converter = pyttsx3.init()

    # Set properties based on the mode
    if mode == 1:
        # Normal voice
        converter.setProperty('rate', 180)  # Normal speed
        converter.setProperty('volume', 1.0)
        voices = converter.getProperty('voices')
        converter.setProperty('voice', voices[0].id)  # Typically the first voice is male
    elif mode == 2:
        # Placeholder for a different type of voice
        converter.setProperty('rate', 170)
        converter.setProperty('volume', 1.0)
        voices = converter.getProperty('voices')
        converter.setProperty('voice', voices[1].id)  # Change the index for a different voice
    # Add more elif blocks for other modes

    # wait for intro sound to finish
    time.sleep(config.MONITOR_GAME_SLEEP_SECONDS)

    # Say the text
    converter.say(text)

    # Wait for the speech to finish
    converter.runAndWait()

# You can add more functions or modify this one for additional features
# USAGE:
'''
    #if same directory as this file, which is /api
    from .text2speech import speak_text 

    # Using the function with different modes
                speak_text("is StarCraft 2 on?", mode=1)
                speak_text("is StarCraft 2 on?", mode=2)
                # Add more calls with different modes as you define them
'''
