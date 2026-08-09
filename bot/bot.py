import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from telebot.async_telebot import AsyncTeleBot
from telebot.types import BotCommand

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# my lib
from cogs import cog__init__, commandnames
from cogs.commands.timetable import (
    TimetableUnavailable,
    check_and_send_notifications,
    migrate_legacy_user_data,
    track_telegram_user,
)

BOT_TOKEN = os.getenv('BOT_TOKEN')

if BOT_TOKEN is None:
    raise ValueError("TOKEN is missing")

bot = AsyncTeleBot(BOT_TOKEN)

name = commandnames
command = cog__init__.Commands(bot)

async def set_commands():
    await bot.delete_my_commands(scope=None, language_code=None)

    commands = [
        BotCommand(name, description)
        for name, description in zip(name.commandsname, name.commanddescript)
    ]

    await bot.set_my_commands(commands[:len(commandnames.commandsname)])

    cmd = await bot.get_my_commands(scope=None, language_code=None)
    print([c.to_json() for c in cmd])

@bot.message_handler(commands=["hello", "start"])
async def start_command(message):
    await track_telegram_user(message)
    await command.start_text(message)

@bot.message_handler(commands=["help"])
async def help_command(message):
    await track_telegram_user(message)
    await command.help(message)

@bot.message_handler(commands=["links"])
async def links_command(message):
    await track_telegram_user(message)
    await command.links(message)

@bot.message_handler(commands=["table"])
async def timetable_command(message):
    await command.timetable(message)

# -----------------------------------------------------------------------------------------------

@bot.callback_query_handler(func=lambda call: True)
async def callback_query(call):
    await command.handle_timetable_callback(call)

@bot.message_handler(func=lambda message: True)
async def message_handler(message):
    await command.handle_timetable_message(message)

async def main():
    print("Bot is starting...")
    try:
        await migrate_legacy_user_data()
    except (TimetableUnavailable, OSError, ValueError) as exc:
        print(f"Legacy user migration will be retried on the next restart: {exc}")
    await set_commands()
    print("Commands set. Bot is now polling...")

    # Start the notification checker
    notification_task = asyncio.create_task(check_and_send_notifications(bot))

    try:
        await bot.infinity_polling()
    finally:
        notification_task.cancel()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Runtime error: {e}")
# ==========================================================================================================================
