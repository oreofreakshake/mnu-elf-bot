import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

async def links(bot, message):
    with open('links.json', 'r') as file:
        links_data = json.load(file)
    
    markup = InlineKeyboardMarkup()
    buttons = []
    for name, url in links_data.items():
        button_text = {
            "moodle": "Moodle",
            "self-service": "Self Service",
            "exam-portal": "Exam Portal",
            "academic-calander": "Calendar",
            "past-papers": "Past Papers"
        }[name]
        buttons.append(InlineKeyboardButton(text=button_text, url=url))
    
    for i in range(0, len(buttons), 2):
        row = buttons[i:i+2]
        markup.row(*row)
    
    await bot.send_message(
        message.chat.id,
        "Here are the important links",
        reply_markup=markup
    )
