
# commands
from cogs.commands.help import help
from cogs.commands.timetable import timetable, timetable_callback, process_timetable_message
from cogs.commands.deadlines import deadlines
from cogs.commands.exam.exam import exam
from cogs.commands.links import links



class Commands:
    def __init__(self, bot):
        self.bot = bot

    async def start_text(self, message):  # ✅
        await self.bot.send_message(
            message.chat.id,
            f"""Hello 👋\nUse /help for every command details\n\nJoin https://t.me/MNUelf for updates""",
        )

    # -----------------------------------------------------------------------------------------------

    async def help(self, message):
        await help(self.bot, message)

    async def links(self, message):
        await links(self.bot, message)

    async def timetable(self, message):
        await timetable(self.bot, message)

    async def deadlines(self, message):
        await deadlines(self.bot, message)

    async def exam(self, message):
        await exam(self.bot, message)

    async def handle_timetable_callback(self, call):
        await timetable_callback(self.bot, call)

    async def handle_timetable_message(self, message):
        await process_timetable_message(self.bot, message)

print("Commands successfully initialized!\n")