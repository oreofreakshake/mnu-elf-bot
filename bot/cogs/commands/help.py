async def help(bot, message):
    commands = {
        "help": "• Bot's guide - you are here",
        "links": "• Get useful university links",
        "table": "• Manage your personalized class schedule",
    }
    lines = [
        "Here are the commands you can use:",
        "",
        *[f"/{command}\n{description}" for command, description in commands.items()],
    ]
    await bot.send_message(message.chat.id, "\n".join(lines))
