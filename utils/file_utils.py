import os
import globals
import time
from datetime import datetime, timedelta


def find_latest_file(folder, file_extension, logger):
    try:
        if not os.path.isdir(folder):
            logger.debug(
                f"The provided path '{folder}' is not a directory. Please provide a valid directory path.")
            return None

        if not file_extension.startswith('.'):
            file_extension = '.' + file_extension

        logger.debug(
            f"Searching for files with extension '{file_extension}' in folder '{folder}' & subdirectories...")

        latest_file = None
        latest_timestamp = None

        for root, _, files in os.walk(folder):
            for filename in files:
                if filename.endswith(file_extension):
                    filepath = os.path.join(root, filename)
                    file_timestamp = os.path.getmtime(filepath)

                    if latest_file is None or file_timestamp > latest_timestamp:
                        latest_file = filepath
                        latest_timestamp = file_timestamp

        if latest_file:
            if latest_file == globals.latest_file_found:
                logger.debug(
                    f"The latest file with extension '{file_extension}' has not changed: {latest_file}")
            else:
                logger.debug(
                    f"Found a new latest file with extension '{file_extension}': {latest_file}")
                globals.latest_file_found = latest_file

            return latest_file
        else:
            logger.debug(
                f"No files with extension '{file_extension}' were found in the folder '{folder}' and its subdirectories.")
            return None

    except Exception as e:
        logger.debug(
            f"An error occurred while searching for the latest file: {e}")
        return None
    
def find_recent_file_within_time(folder, file_extension, minutes, retries, logger, last_processed_file=None):
    """
    Find the most recent file within a time period or newer than the last processed file.
    """
    attempt = 0
    while attempt <= retries:
        try:
            # Find the latest file
            latest_file = find_latest_file(folder, file_extension, logger)
            if latest_file:
                file_timestamp = os.path.getmtime(latest_file)
                is_recent = datetime.now() - datetime.fromtimestamp(file_timestamp) <= timedelta(minutes=minutes)
                is_newer_than_last = last_processed_file is None or file_timestamp > os.path.getmtime(last_processed_file)

                if is_recent or is_newer_than_last:
                    logger.debug(f"New file found: {latest_file}")
                    return latest_file

            logger.debug(f"No new file found in folder '{folder}'.")
        except Exception as e:
            logger.error(f"Error while searching for files: {e}")
            return None

        if attempt < retries:
            logger.debug(f"Retrying in {minutes} minute(s)... (Attempt {attempt + 1}/{retries})")
            time.sleep(minutes * 60)
        attempt += 1

    logger.debug("No new files found after retries.")
    return None
