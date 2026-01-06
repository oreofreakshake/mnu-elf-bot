import json
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from prettytable import PrettyTable
import asyncio
from datetime import datetime, timedelta

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# timetable DB
with open(os.path.join(ROOT_DIR, 'timetable.json'), 'r') as file:
    timetable_data = json.load(file)

# user DB
USER_DATA_FILE = os.path.join(ROOT_DIR, 'user.json')

def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r') as file:
            return json.load(file)
    return {}

def save_user_data(data):
    with open(USER_DATA_FILE, 'w') as file:
        json.dump(data, file, indent=2)

user_subjects = load_user_data()
user_states = {}

def create_timetable_markup():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("Add Subject", callback_data="add_subject"),
                InlineKeyboardButton("Remove Subject", callback_data="remove_subject"))
    markup.row(InlineKeyboardButton("View Timetable", callback_data="view_timetable"))
    return markup

def find_subject(subject_code):
    lecture = None
    tutorial = None
    for course in timetable_data['schedule']:
        for subject in course['subjects']:
            if subject['subCode'] == subject_code:
                if subject['L'] and not lecture:
                    lecture = subject
                elif not subject['L'] and not tutorial:
                    tutorial = subject
                if lecture and tutorial:
                    return [lecture, tutorial]
    return [lecture, tutorial] if lecture or tutorial else []

def format_timetable(subjects):
    if not subjects:
        return ["📅 Your timetable is empty"]
    
    tables = []
    
    for subject_group in subjects:
        if not subject_group:
            continue
        
        subject_name = subject_group[0]['subName']
        table = PrettyTable()
        table.field_names = ["Code", "Time", "Room", "Type"]
        table.align["Code"] = "l"
        table.align["Time"] = "l"
        table.align["Room"] = "l"
        table.align["Type"] = "l"
        
        for subject in subject_group:
            if subject:
                code = subject['subCode']
                time = subject['time']
                room = subject['room']
                type = "L" if subject['L'] else "T"
                
                table.add_row([code, time, room, type])
        
        formatted_table = f"*{subject_name}*\n```\n{table}```\n\n"
        tables.append(formatted_table)
    
    return tables

async def check_and_send_notifications(bot):
    while True:
        current_time = datetime.now()
        current_day = current_time.strftime("%a").lower()
        for chat_id, subjects in user_subjects.items():
            for subject_group in subjects:
                for subject in subject_group:
                    day, start_time, _ = subject['time'].split('-')
                    if day.lower() != current_day:
                        continue
                    
                    class_time = datetime.strptime(start_time, "%H%M").time()
                    class_time = datetime.combine(current_time.date(), class_time)
                    
                    time_diff = class_time - current_time
                    if timedelta(0) < time_diff <= timedelta(minutes=30):
                        remaining_minutes = int(time_diff.total_seconds() / 60)
                        notification_message = (
                            f"You have {subject['subName']} "
                            f"{'lecture' if subject['L'] else 'tutorial'} in {remaining_minutes} minutes!\n"
                            f"Room: {subject['room']}"
                        )
                        await bot.send_message(chat_id, notification_message)
        
        await asyncio.sleep(600)

async def timetable(bot, message):
    global user_states
    chat_id = str(message.chat.id)
    if chat_id not in user_subjects:
        user_subjects[chat_id] = []
        save_user_data(user_subjects)
    user_states[chat_id] = 'MAIN_MENU'
    await bot.send_message(chat_id, "Timetable Dashboard", reply_markup=create_timetable_markup())

    if not hasattr(bot, 'notification_task'):
        bot.notification_task = asyncio.create_task(check_and_send_notifications(bot))

async def timetable_callback(bot, call):
    global user_states
    chat_id = str(call.message.chat.id)
    
    if call.data == "add_subject":
        await bot.answer_callback_query(call.id)
        if len(user_subjects.get(chat_id, [])) >= 4:
            await bot.send_message(chat_id, "You've reached the maximum of 4 subjects")
        else:
            user_states[chat_id] = 'WAITING_FOR_SUBJECT_CODE'
            await bot.send_message(chat_id, "Enter the subject code you'd like to add:")
    
    elif call.data == "remove_subject":
        await bot.answer_callback_query(call.id)
        if not user_subjects.get(chat_id):
            await bot.send_message(chat_id, "You have nothing to remove")
        else:
            markup = InlineKeyboardMarkup()
            for subject_group in user_subjects[chat_id]:
                subject_code = subject_group[0]['subCode']
                markup.add(InlineKeyboardButton(subject_code, callback_data=f"remove_{subject_code}"))
            await bot.send_message(chat_id, "Select a subject to remove:", reply_markup=markup)
    
    elif call.data.startswith("remove_"):
        subject_code = call.data.split("_")[1]
        user_subjects[chat_id] = [s for s in user_subjects[chat_id] if s[0]['subCode'] != subject_code]
        save_user_data(user_subjects)
        await bot.answer_callback_query(call.id, f"Removed {subject_code} from your timetable")
        await bot.send_message(chat_id, f"{subject_code} removed")

        # Show the updated list of subjects
        if user_subjects[chat_id]:
            subject_list = "\n".join([f"{s[0]['subCode']} : {s[0]['subName']}" for s in user_subjects[chat_id]])
            await bot.send_message(chat_id, f"Your current subjects:\n\n{subject_list}")
        else:
            await bot.send_message(chat_id, "Your timetable is now empty")

        await bot.send_message(chat_id, "What would you like to do next?", reply_markup=create_timetable_markup())
    
    elif call.data == "view_timetable":
        await bot.answer_callback_query(call.id)
        timetable_tables = format_timetable(user_subjects.get(chat_id, []))
        if len(timetable_tables) == 1 and timetable_tables[0] == "📅 Your timetable is empty":
            await bot.send_message(chat_id, timetable_tables[0])
        else:
            for table in timetable_tables:
                await bot.send_message(chat_id, table, parse_mode='Markdown')

async def handle_message(bot, message):
    global user_states
    chat_id = str(message.chat.id)
    
    if chat_id in user_states and user_states[chat_id] == 'WAITING_FOR_SUBJECT_CODE':
        subject_code = message.text.upper()
        subjects = find_subject(subject_code)
        
        if subjects:
            if chat_id not in user_subjects:
                user_subjects[chat_id] = []
            
            if not any(s[0]['subCode'] == subject_code for s in user_subjects[chat_id]):
                user_subjects[chat_id].append([s for s in subjects if s])
                save_user_data(user_subjects)
                await bot.send_message(chat_id, f"Added {subject_code} to your timetable")
                
                # Show the list of subjects
                subject_list = "\n".join([f"{s[0]['subCode']} : {s[0]['subName']}" for s in user_subjects[chat_id]])
                await bot.send_message(chat_id, f"Your current subjects:\n\n{subject_list}")
            else:
                await bot.send_message(chat_id, f"{subject_code} is already in your timetable")
        else:
            await bot.send_message(chat_id, f"Subject code not found")
        
        user_states[chat_id] = 'MAIN_MENU'
        await bot.send_message(chat_id, "What would you like to do next?", reply_markup=create_timetable_markup())

async def process_timetable_message(bot, message):
    await handle_message(bot, message)
