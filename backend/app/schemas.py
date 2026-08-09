from typing import Any

from pydantic import BaseModel, Field


class EntryUpdate(BaseModel):
    sub_code: str = Field(min_length=1, max_length=32)
    subject_name: str = Field(min_length=1)
    session_type: str = Field(min_length=1, max_length=16)
    lecturer: str = Field(min_length=1)
    time: str = Field(min_length=1, max_length=64)
    room: str = Field(min_length=1)


class IssueResolve(BaseModel):
    corrected_data: dict[str, Any] | None = None


class TelegramUserSync(BaseModel):
    telegram_user_id: int
    notification_chat_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    language_code: str | None = None


class SubjectSelectionCreate(BaseModel):
    course: str = Field(max_length=100)
    subject_code: str = Field(min_length=1, max_length=32)


class TelegramLogin(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


class UserRoleUpdate(BaseModel):
    role: str = Field(pattern="^(user|reviewer|admin)$")


class DevelopmentLogin(BaseModel):
    token: str = Field(min_length=1)
