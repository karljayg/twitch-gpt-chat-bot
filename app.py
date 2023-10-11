import asyncio

from api.twitch_bot import TwitchBot


async def tasks_to_do():
    try:
        # Create an instance of the bot and start it
        bot = TwitchBot()
        await bot.start()
    except SystemExit as e:
        # Handle the SystemExit exception if needed, or pass to suppress it
        pass


async def main():
    tasks = [asyncio.create_task(tasks_to_do())]
    for task in tasks:
        await task  # Await the task here to handle exceptions

asyncio.run(main())
