import os
import asyncio
from telebot.async_telebot import AsyncTeleBot
from telebot.types import BotCommand
from dotenv import load_dotenv

load_dotenv()

# my lib
from cogs import cog__init__, commandnames
from cogs.commands.timetable import check_and_send_notifications

BOT_TOKEN = os.getenv('BOT_TOKEN')

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
    await command.start_text(message)

@bot.message_handler(commands=["help"])
async def help_command(message):
    await command.help(message)

@bot.message_handler(commands=["links"])
async def links_command(message):
    await command.links(message)

@bot.message_handler(commands=["table"])
async def timetable_command(message):
    await command.timetable(message)

@bot.message_handler(commands=["dues"])
async def deadline_command(message):
    await command.deadlines(message)

@bot.message_handler(commands=["exam"])
async def exam_command(message):
    await command.exam(message)

# -----------------------------------------------------------------------------------------------

@bot.callback_query_handler(func=lambda call: True)
async def callback_query(call):
    await command.handle_timetable_callback(call)

@bot.message_handler(func=lambda message: True)
async def message_handler(message):
    await command.handle_timetable_message(message)

async def main():
    print("Bot is starting...")
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
