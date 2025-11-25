import logging
import sys

class SmartNewlineFormatter(logging.Formatter):
    """
    Formatter that ensures log messages starting with a timestamp 
    always start on a new line if the previous output was not a newline.
    """
    def __init__(self, fmt=None, datefmt=None, style='%'):
        super().__init__(fmt, datefmt, style)
        self.last_char_was_newline = True

    def format(self, record):
        msg = super().format(record)
        
        # If we're printing to console (which is usually where the heartbeats are),
        # we want to ensure separation.
        # Note: This logic assumes this formatter is used for the console handler.
        
        # We can't easily know the *actual* state of stdout here since other things print to it.
        # But we can force a newline if the message starts with a timestamp (which our format does).
        
        return "\n" + msg if not msg.startswith("\n") else msg

class NewlineStreamHandler(logging.StreamHandler):
    """
    StreamHandler that prepends a newline to log records if necessary
    to separate them from heartbeat indicators like '...'.
    """
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            
            # Check if the last char written to stream was a newline?
            # It's hard to check stream state directly in standard python logging.
            # Instead, we just prepend '\n' because we assume heartbeats 
            # (print('.')) left us mid-line.
            
            # To avoid double newlines when there WAS a newline, we can be smarter 
            # if we controlled the heartbeat printing too, but here we just 
            # want to ensure the log header starts clean.
            
            # Simple approach: Always prepend newline. 
            # Disadvantage: might get extra blank lines. 
            # Advantage: heartbeats never clutter log lines.
            
            # Better approach for this specific user request:
            # The user sees `..2025...`
            # They want `..\n2025...`
            
            stream.write('\n' + msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


