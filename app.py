import sys
import asyncio
from api.twitch_bot import TwitchBot, logger
from settings import config

# Check for command-line arguments to override config values
if len(sys.argv) > 1:
    for arg in sys.argv[1:]:
        if "PLAYER_INTROS_ENABLED=" in arg:
            # Extract the value and convert it to a boolean
            value = arg.split("=")[1].lower()
            config.PLAYER_INTROS_ENABLED = value == "true"
            print(f"PLAYER_INTROS_ENABLED set to: {config.PLAYER_INTROS_ENABLED}")

async def tasks_to_do():
    try:
        bot = TwitchBot()
        await bot.start()
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        # Optionally, you might want to restart the bot after a delay
        # await asyncio.sleep(60)
        # return await tasks_to_do()  # Restart the task

async def main():
    while True:
        try:
            task = asyncio.create_task(tasks_to_do())
            await task
        except asyncio.CancelledError:
            logger.info("Task was cancelled. Shutting down.")
            break
        except Exception as e:
            logger.exception(f"An error occurred in the main loop: {e}")
            await asyncio.sleep(60)  # Wait for 60 seconds before restarting

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down.")
    except Exception as e:
        logger.exception(f"Fatal error in main script: {e}")