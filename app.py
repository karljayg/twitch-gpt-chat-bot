import sys
import asyncio
from api.twitch_bot import TwitchBot, logger
from api.discord_bot import start_discord_bot
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
    logger.info("=== TASKS_TO_DO FUNCTION STARTED ===")
    try:
        # Start Twitch bot
        logger.info("Creating Twitch bot instance...")
        twitch_bot = TwitchBot()
        logger.info("Twitch bot instance created")
        
        # Create tasks for both bots
        tasks = []
        
        # Add Twitch bot task - run in thread since IRC bot is blocking
        logger.info("Creating Twitch bot task...")
        loop = asyncio.get_event_loop()
        twitch_task = loop.run_in_executor(None, twitch_bot.start)
        tasks.append(twitch_task)
        logger.info("Twitch bot task created and added to task list (running in thread)")
        
        # Start Discord bot if enabled
        discord_enabled = hasattr(config, 'DISCORD_ENABLED') and getattr(config, 'DISCORD_ENABLED', False)
        logger.info("=== DISCORD BOT STARTUP CHECK ===")
        logger.info(f"Discord enabled: {discord_enabled}")
        logger.info(f"Discord config check - DISCORD_TOKEN: {'SET' if getattr(config, 'DISCORD_TOKEN', '') else 'EMPTY'}")
        logger.info(f"Discord config check - DISCORD_CHANNEL_ID: {getattr(config, 'DISCORD_CHANNEL_ID', 'NOT_SET')}")
        
        if discord_enabled:
            try:
                # Start Discord bot concurrently
                logger.info("Creating Discord bot task...")
                discord_task = asyncio.create_task(start_discord_bot(twitch_bot))
                tasks.append(discord_task)
                logger.info("Discord bot task created and added to task list")
                logger.info(f"Total tasks to run: {len(tasks)} (Twitch + Discord)")
                
                # Give Discord task a moment to start connecting
                logger.info("Allowing Discord task to begin startup...")
                await asyncio.sleep(0.5)
            except Exception as discord_error:
                logger.error(f"Failed to create Discord bot task: {discord_error}")
                logger.exception("Discord bot task creation exception:")
        else:
            logger.info("Discord bot is disabled or not configured")
            logger.info(f"Total tasks to run: {len(tasks)} (Twitch only)")
        
        # Run both bots concurrently
        logger.info("Starting all bot tasks...")
        logger.info(f"About to run {len(tasks)} tasks concurrently...")
        
        # Use asyncio.gather with return_exceptions to ensure both tasks start
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(f"All tasks completed. Results: {results}")
        except Exception as e:
            logger.error(f"Error in task execution: {e}")
            logger.exception("Task execution exception:")
        
    except Exception as e:
        logger.exception(f"An unexpected error occurred in tasks_to_do: {e}")
        # Optionally, you might want to restart the bot after a delay
        # await asyncio.sleep(60)
        # return await tasks_to_do()  # Restart the task

async def main():
    logger.info("=== MAIN FUNCTION STARTED ===")
    while True:
        try:
            logger.info("Creating main task...")
            task = asyncio.create_task(tasks_to_do())
            logger.info("Main task created, awaiting completion...")
            await task
            logger.info("Main task completed")
        except asyncio.CancelledError:
            logger.info("Task was cancelled. Shutting down.")
            break
        except Exception as e:
            logger.exception(f"An error occurred in the main loop: {e}")
            await asyncio.sleep(60)  # Wait for 60 seconds before restarting

if __name__ == "__main__":
    logger.info("=== APPLICATION STARTING ===")
    try:
        logger.info("Starting asyncio.run(main())...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down.")
    except Exception as e:
        logger.exception(f"Fatal error in main script: {e}")