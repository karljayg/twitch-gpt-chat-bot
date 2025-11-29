import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

try:
    from utils.wiki_utils import wikipedia_question
    print("Attempting to run wikipedia_question...")
    result = wikipedia_question("Who won the 2024 Super Bowl?")
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()











