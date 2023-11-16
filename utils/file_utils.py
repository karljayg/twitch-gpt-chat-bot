import os

def find_latest_file(folder, file_extension, logger):
    latest_file_found = None
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
            if latest_file == latest_file_found:
                logger.debug(
                    f"The latest file with extension '{file_extension}' has not changed: {latest_file}")
            else:
                logger.debug(
                    f"Found a new latest file with extension '{file_extension}': {latest_file}")
                latest_file_found = latest_file

            return latest_file
        else:
            logger.debug(
                f"No files with extension '{file_extension}' were found in the folder '{folder}' and its subdirectories.")
            return None

    except Exception as e:
        logger.debug(
            f"An error occurred while searching for the latest file: {e}")
        return None
