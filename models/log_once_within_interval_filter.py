from datetime import datetime, timedelta
from difflib import SequenceMatcher
import logging
import math

class LogOnceWithinIntervalFilter(logging.Filter):
    """Logs each unique message only once within a specified time interval if they are similar."""

    def __init__(self, similarity_threshold=0.95, interval_seconds=120):
        super().__init__()
        self.similarity_threshold = similarity_threshold
        self.interval = timedelta(seconds=interval_seconds)
        self.last_logged_message = None
        self.last_logged_time = None
        self.loop_count = 0  # Initialize the loop counter
        self.loops_to_print = 5  # Number of loops to wait before printing

    # log filter for similar repetitive messages to suppress
    def filter(self, record):
        now = datetime.now()
        time_left = None
        self.loop_count += 1  # Increment the loop counter
        time_left = ...  # Calculate the time left
        time_since_last_logged = ...  # Calculate the time since last logged

        if self.last_logged_message:
            time_since_last_logged = now - self.last_logged_time
            time_left = self.interval - time_since_last_logged
            if time_since_last_logged < self.interval:
                similarity = SequenceMatcher(
                    None, self.last_logged_message, record.msg).ratio()
                if similarity > self.similarity_threshold:
                    if self.loop_count % self.loops_to_print == 0:  # Check if it's time to print
                        print(
                            f"suppressed: {math.floor(time_left.total_seconds())} secs")
                    return False

        self.last_logged_message = record.msg
        self.last_logged_time = now
        return True
