#!/usr/bin/env python3

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, TypeAlias, cast
from zoneinfo import ZoneInfo

import aiohttp
from prettytable import PrettyTable
from telebot.apihelper import ApiTelegramException
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("BOT_DATA_DIR", ROOT_DIR / "data"))
USER_DATA_FILE = DATA_DIR / "user.json"
LEGACY_MIGRATION_MARKER = DATA_DIR / ".postgres-user-migration-complete"
TIMETABLE_API_URL = os.getenv("TIMETABLE_API_URL", "http://localhost:8000/api").rstrip("/")
BOT_SERVICE_TOKEN = os.getenv("BOT_SERVICE_TOKEN", "local-development-token")
BOT_TIMEZONE = ZoneInfo(os.getenv("BOT_TIMEZONE", "Indian/Maldives"))
TIMETABLE_CACHE_SECONDS = int(os.getenv("TIMETABLE_CACHE_SECONDS", "60"))

DATA_DIR.mkdir(parents=True, exist_ok=True)

JsonDict: TypeAlias = dict[str, Any]
Schedule: TypeAlias = list[JsonDict]


class TimetableUnavailable(RuntimeError):
    pass


class TimetableClient:
    def __init__(self) -> None:
        self._schedule: Schedule | None = None
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    async def get_schedule(self, force: bool = False) -> Schedule:
        if not force and self._schedule is not None and time.monotonic() < self._expires_at:
            return self._schedule
        async with self._lock:
            if not force and self._schedule is not None and time.monotonic() < self._expires_at:
                return self._schedule
            timeout = aiohttp.ClientTimeout(total=15)
            try:
                async with (
                    aiohttp.ClientSession(timeout=timeout) as session,
                    session.get(f"{TIMETABLE_API_URL}/timetable") as response,
                ):
                    if response.status == 404:
                        raise TimetableUnavailable("No timetable has been published yet.")
                    response.raise_for_status()
                    payload: Any = await response.json()
            except TimetableUnavailable:
                raise
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                raise TimetableUnavailable("The timetable service is temporarily unavailable.") from exc
            schedule_value = payload.get("schedule") if isinstance(payload, dict) else None
            if not isinstance(schedule_value, list) or not all(
                isinstance(section, dict) for section in schedule_value
            ):
                raise TimetableUnavailable("The timetable service returned invalid data.")
            schedule = cast(Schedule, schedule_value)
            self._schedule = schedule
            self._expires_at = time.monotonic() + TIMETABLE_CACHE_SECONDS
            return schedule


class BotDataClient:
    async def _request(
        self, method: str, path: str, payload: JsonDict | None = None
    ) -> Any:
        timeout = aiohttp.ClientTimeout(total=15)
        headers = {"X-Bot-Token": BOT_SERVICE_TOKEN}
        try:
            async with (
                aiohttp.ClientSession(timeout=timeout, headers=headers) as session,
                session.request(
                    method, f"{TIMETABLE_API_URL}{path}", json=payload
                ) as response,
            ):
                body: Any = await response.json()
                if response.status >= 400:
                    detail = body.get("detail") if isinstance(body, dict) else None
                    raise TimetableUnavailable(detail or "The bot data service rejected the request.")
                return body
        except TimetableUnavailable:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as exc:
            raise TimetableUnavailable("The bot data service is temporarily unavailable.") from exc

    async def sync_user(self, telegram_user: Any, chat_id: int) -> None:
        await self.sync_user_values(
            telegram_user_id=int(telegram_user.id),
            chat_id=chat_id,
            username=getattr(telegram_user, "username", None),
            first_name=getattr(telegram_user, "first_name", None),
            last_name=getattr(telegram_user, "last_name", None),
            language_code=getattr(telegram_user, "language_code", None),
        )

    async def sync_user_values(
        self,
        telegram_user_id: int,
        chat_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        language_code: str | None = None,
    ) -> None:
        await self._request(
            "POST",
            "/bot/users/sync",
            {
                "telegram_user_id": telegram_user_id,
                "notification_chat_id": chat_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "language_code": language_code,
            },
        )

    async def get_subjects(self, telegram_user_id: int) -> list[JsonDict]:
        result = await self._request("GET", f"/bot/users/{telegram_user_id}/subjects")
        if not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
            raise TimetableUnavailable("The bot data service returned invalid subjects.")
        return cast(list[JsonDict], result)

    async def add_subject(
        self, telegram_user_id: int, course: str, subject_code: str
    ) -> JsonDict:
        result = await self._request(
            "POST",
            f"/bot/users/{telegram_user_id}/subjects",
            {"course": course, "subject_code": subject_code},
        )
        if not isinstance(result, dict):
            raise TimetableUnavailable("The bot data service returned an invalid subject.")
        return cast(JsonDict, result)

    async def remove_subject(self, telegram_user_id: int, subject_id: str) -> None:
        await self._request(
            "DELETE", f"/bot/users/{telegram_user_id}/subjects/{subject_id}"
        )

    async def get_subscriptions(self) -> list[JsonDict]:
        result = await self._request("GET", "/bot/subscriptions")
        if not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
            raise TimetableUnavailable("The bot data service returned invalid subscriptions.")
        return cast(list[JsonDict], result)


timetable_client = TimetableClient()
bot_data_client = BotDataClient()
user_states: dict[str, str] = {}
pending_offerings: dict[str, list[JsonDict]] = {}
sent_notifications: set[tuple[str, str, str, str, str]] = set()


def load_user_data() -> dict[str, list[JsonDict]]:
    if not USER_DATA_FILE.exists():
        return {}
    try:
        raw = json.loads(USER_DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    migrated: dict[str, list[JsonDict]] = {}
    for chat_id, selections in raw.items():
        migrated[chat_id] = []
        for selection in selections:
            if isinstance(selection, dict) and selection.get("subCode"):
                migrated[chat_id].append(
                    {"course": selection.get("course", ""), "subCode": selection["subCode"]}
                )
            elif isinstance(selection, list) and selection:
                first = next((item for item in selection if isinstance(item, dict)), None)
                if first and first.get("subCode"):
                    migrated[chat_id].append({"course": "", "subCode": first["subCode"]})
            elif isinstance(selection, str):
                migrated[chat_id].append({"course": "", "subCode": selection.upper()})
    return migrated


async def migrate_legacy_user_data() -> None:
    if LEGACY_MIGRATION_MARKER.exists() or not USER_DATA_FILE.exists():
        return
    legacy_users = load_user_data()
    for chat_id, selections in legacy_users.items():
        numeric_id = int(chat_id)
        await bot_data_client.sync_user_values(numeric_id, numeric_id)
        existing = await bot_data_client.get_subjects(numeric_id)
        existing_keys = {(item.get("course"), item.get("subCode")) for item in existing}
        for selection in selections:
            key = (selection.get("course", ""), selection.get("subCode", ""))
            if key not in existing_keys:
                await bot_data_client.add_subject(numeric_id, key[0], key[1])
    LEGACY_MIGRATION_MARKER.write_text("migrated\n", encoding="utf-8")


def create_timetable_markup() -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("Add Subject", callback_data="add_subject"),
        InlineKeyboardButton("Remove Subject", callback_data="remove_subject"),
    )
    markup.row(InlineKeyboardButton("View Timetable", callback_data="view_timetable"))
    return markup


def find_offerings(subject_code: str, schedule: Schedule) -> list[JsonDict]:
    offerings = []
    for section in schedule:
        sessions = [
            subject for subject in section.get("subjects", [])
            if subject.get("subCode", "").upper() == subject_code.upper()
        ]
        if sessions:
            offerings.append(
                {
                    "course": section["course"],
                    "semester": section["semester"],
                    "subCode": subject_code.upper(),
                    "subjects": sessions,
                }
            )
    return offerings


def resolve_selection(selection: JsonDict, schedule: Schedule) -> JsonDict | None:
    offerings = find_offerings(selection["subCode"], schedule)
    if not offerings:
        return None
    if selection.get("course"):
        return next((item for item in offerings if item["course"] == selection["course"]), None)
    return offerings[0]


def selection_label(selection: JsonDict) -> str:
    course = f" · {selection['course']}" if selection.get("course") else ""
    return f"{selection['subCode']}{course}"


def format_timetable(offerings: list[JsonDict]) -> list[str]:
    if not offerings:
        return ["📅 Your timetable is empty"]
    tables = []
    for offering in offerings:
        subjects = offering["subjects"]
        if not subjects:
            continue
        table = PrettyTable()
        table.field_names = ["Time", "Room", "Type"]
        for field in table.field_names:
            table.align[field] = "l"
        for subject in subjects:
            session_type = subject.get("sessionType") or ("L" if subject.get("L") else "T")
            table.add_row([subject["time"], subject["room"], session_type])
        heading = f"*{subjects[0]['subName']}* · {offering['course']}"
        tables.append(f"{heading}\n```\n{table}```\n")
    return tables or ["📅 Your timetable is empty"]


async def resolved_user_offerings(
    telegram_user_id: int, force: bool = False
) -> list[JsonDict]:
    schedule = await timetable_client.get_schedule(force=force)
    selections = await bot_data_client.get_subjects(telegram_user_id)
    return [
        offering
        for selection in selections
        if (offering := resolve_selection(selection, schedule)) is not None
    ]


async def check_and_send_notifications(bot) -> None:
    while True:
        try:
            schedule = await timetable_client.get_schedule(force=True)
            now = datetime.now(BOT_TIMEZONE)
            current_day = now.strftime("%a").lower()
            today = now.date().isoformat()
            subscriptions = await bot_data_client.get_subscriptions()
            for subscription in subscriptions:
                chat_id = str(subscription["chatId"])
                selections = subscription.get("subjects", [])
                for selection in selections:
                    offering = resolve_selection(selection, schedule)
                    if not offering:
                        continue
                    for subject in offering["subjects"]:
                        if subject.get("time") == "TBD":
                            continue
                        try:
                            day, start_time, _ = subject["time"].split("-")
                            if day.lower() != current_day:
                                continue
                            parsed_time = datetime.strptime(start_time, "%H%M").replace(
                                tzinfo=BOT_TIMEZONE
                            )
                            class_time = datetime.combine(
                                now.date(), parsed_time.time(), BOT_TIMEZONE
                            )
                        except (ValueError, AttributeError):
                            continue
                        time_diff = class_time - now
                        notification_key = (
                            chat_id,
                            offering["course"],
                            subject["subCode"],
                            subject.get("sessionType", ""),
                            f"{today}-{start_time}",
                        )
                        if timedelta(0) < time_diff <= timedelta(minutes=30) and notification_key not in sent_notifications:
                            sent_notifications.add(notification_key)
                            remaining = max(1, int(time_diff.total_seconds() / 60))
                            session_type = subject.get("sessionType") or ("lecture" if subject.get("L") else "tutorial")
                            await bot.send_message(
                                chat_id,
                                f"⏰ {subject['subName']} ({session_type}) starts in {remaining} minutes.\n"
                                f"Room: {subject['room']}",
                            )
            sent_notifications.intersection_update({key for key in sent_notifications if key[-1].startswith(today)})
        except TimetableUnavailable as exc:
            print(f"Notification check skipped: {exc}")
        except (ApiTelegramException, KeyError, TypeError, ValueError, OSError) as exc:
            print(f"Notification check failed: {exc}")
        await asyncio.sleep(600)


async def timetable(bot, message) -> None:
    chat_id = str(message.chat.id)
    telegram_user_id = int(message.from_user.id)
    await bot_data_client.sync_user(message.from_user, int(message.chat.id))
    user_states[str(telegram_user_id)] = "MAIN_MENU"
    await bot.send_message(chat_id, "Timetable Dashboard", reply_markup=create_timetable_markup())


async def track_telegram_user(message) -> None:
    await bot_data_client.sync_user(message.from_user, int(message.chat.id))


async def add_offering(
    bot, telegram_user_id: int, chat_id: str, offering: JsonDict
) -> None:
    selection = {"course": offering["course"], "subCode": offering["subCode"]}
    selections = await bot_data_client.get_subjects(telegram_user_id)
    if any(
        item.get("course") == selection["course"]
        and item.get("subCode") == selection["subCode"]
        for item in selections
    ):
        await bot.send_message(chat_id, f"{selection_label(selection)} is already in your timetable")
        return
    await bot_data_client.add_subject(
        telegram_user_id, selection["course"], selection["subCode"]
    )
    selections = await bot_data_client.get_subjects(telegram_user_id)
    await bot.send_message(chat_id, f"Added {selection_label(selection)} to your timetable")
    subject_list = "\n".join(f"- {selection_label(item)}" for item in selections)
    await bot.send_message(chat_id, f"Your current subjects:\n\n{subject_list}")


async def timetable_callback(bot, call) -> None:
    chat_id = str(call.message.chat.id)
    telegram_user_id = int(call.from_user.id)
    user_key = str(telegram_user_id)
    await bot_data_client.sync_user(call.from_user, int(call.message.chat.id))
    if call.data == "add_subject":
        await bot.answer_callback_query(call.id)
        selections = await bot_data_client.get_subjects(telegram_user_id)
        if len(selections) >= 4:
            await bot.send_message(chat_id, "You've reached the maximum of 4 subjects")
        else:
            user_states[user_key] = "WAITING_FOR_SUBJECT_CODE"
            await bot.send_message(chat_id, "Enter the subject code you'd like to add:")

    elif call.data == "remove_subject":
        await bot.answer_callback_query(call.id)
        selections = await bot_data_client.get_subjects(telegram_user_id)
        if not selections:
            await bot.send_message(chat_id, "You have nothing to remove")
        else:
            markup = InlineKeyboardMarkup()
            for selection in selections:
                markup.add(
                    InlineKeyboardButton(
                        selection_label(selection),
                        callback_data=f"removesub_{selection['id']}",
                    )
                )
            await bot.send_message(chat_id, "Select a subject to remove:", reply_markup=markup)

    elif call.data.startswith("removesub_"):
        await bot.answer_callback_query(call.id)
        subject_id = call.data.removeprefix("removesub_")
        selections = await bot_data_client.get_subjects(telegram_user_id)
        removed = next((item for item in selections if item.get("id") == subject_id), None)
        if removed is None:
            await bot.send_message(chat_id, "That selection is no longer available.")
            return
        await bot_data_client.remove_subject(telegram_user_id, subject_id)
        await bot.send_message(chat_id, f"Removed {selection_label(removed)}")
        await bot.send_message(chat_id, "What would you like to do next?", reply_markup=create_timetable_markup())

    elif call.data.startswith("offering_"):
        await bot.answer_callback_query(call.id)
        try:
            index = int(call.data.removeprefix("offering_"))
            offering = pending_offerings[user_key][index]
        except (ValueError, IndexError, KeyError):
            await bot.send_message(chat_id, "That offering expired. Please add the subject again.")
            return
        await add_offering(bot, telegram_user_id, chat_id, offering)
        pending_offerings.pop(user_key, None)
        user_states[user_key] = "MAIN_MENU"
        await bot.send_message(chat_id, "What would you like to do next?", reply_markup=create_timetable_markup())

    elif call.data == "view_timetable":
        await bot.answer_callback_query(call.id)
        try:
            # User-requested views should always reflect the latest verified
            # values from the currently published document.
            offerings = await resolved_user_offerings(telegram_user_id, force=True)
            for table in format_timetable(offerings):
                await bot.send_message(chat_id, table, parse_mode="Markdown")
        except TimetableUnavailable as exc:
            await bot.send_message(chat_id, f"⚠️ {exc}")


async def handle_message(bot, message) -> None:
    chat_id = str(message.chat.id)
    telegram_user_id = int(message.from_user.id)
    user_key = str(telegram_user_id)
    if user_states.get(user_key) != "WAITING_FOR_SUBJECT_CODE" or not message.text:
        return
    await bot_data_client.sync_user(message.from_user, int(message.chat.id))
    subject_code = message.text.strip().upper()
    try:
        schedule = await timetable_client.get_schedule(force=True)
        offerings = find_offerings(subject_code, schedule)
    except TimetableUnavailable as exc:
        await bot.send_message(chat_id, f"⚠️ {exc}")
        return

    if not offerings:
        await bot.send_message(chat_id, "Subject code not found in the published timetable")
    elif len(offerings) == 1:
        await add_offering(bot, telegram_user_id, chat_id, offerings[0])
    else:
        pending_offerings[user_key] = offerings
        markup = InlineKeyboardMarkup()
        for index, offering in enumerate(offerings):
            markup.add(
                InlineKeyboardButton(
                    f"{offering['course']} · Semester {offering['semester']}",
                    callback_data=f"offering_{index}",
                )
            )
        await bot.send_message(chat_id, "This subject appears in multiple courses. Choose yours:", reply_markup=markup)
        return

    user_states[user_key] = "MAIN_MENU"
    await bot.send_message(chat_id, "What would you like to do next?", reply_markup=create_timetable_markup())


async def process_timetable_message(bot, message) -> None:
    await handle_message(bot, message)
