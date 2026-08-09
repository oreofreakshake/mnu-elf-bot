from cogs.commands.help import help
from cogs.commands.links import links
from cogs.commands.timetable import (
    process_timetable_message,
    timetable,
    timetable_callback,
)


class Commands:
    def __init__(self, bot):
        self.bot = bot

    async def start_text(self, message):
        await self.bot.send_message(
            message.chat.id,
            "Hello 👋\nUse /help to see every command.\n\n"
            "Join https://t.me/MNUelf for updates.",
        )

    async def help(self, message):
        await help(self.bot, message)

    async def links(self, message):
        await links(self.bot, message)

    async def timetable(self, message):
        await timetable(self.bot, message)

    async def handle_timetable_callback(self, call):
        await timetable_callback(self.bot, call)

    async def handle_timetable_message(self, message):
        await process_timetable_message(self.bot, message)


print("Commands successfully initialized!")
