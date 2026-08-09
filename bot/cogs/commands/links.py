import json
from pathlib import Path

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


LINKS_FILE = Path(__file__).resolve().parents[2] / "links.json"


async def links(bot, message):
    links_data = json.loads(LINKS_FILE.read_text(encoding="utf-8"))
    labels = {
        "moodle": "Moodle",
        "self-service": "Self Service",
        "exam-portal": "Exam Portal",
        "academic-calander": "Calendar",
        "past-papers": "Past Papers",
    }
    buttons = [
        InlineKeyboardButton(text=labels[name], url=url)
        for name, url in links_data.items()
    ]
    markup = InlineKeyboardMarkup()
    for index in range(0, len(buttons), 2):
        markup.row(*buttons[index : index + 2])
    await bot.send_message(message.chat.id, "Here are the important links", reply_markup=markup)
