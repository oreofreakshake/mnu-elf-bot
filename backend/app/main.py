import hashlib
import hmac
import json
import secrets
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from fastapi import Cookie, Depends, FastAPI, File, Header, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import func, select, update as sql_update
from sqlalchemy.orm import Session, selectinload

from .config import settings
from .database import get_session, init_database
from .models import (
    Document,
    ExtractionIssue,
    ScheduleEntry,
    ScheduleSection,
    AdminSession,
    TelegramUser,
    UserSubject,
    utcnow,
)
from .parser import clean, validate
from .schemas import (
    EntryUpdate,
    DevelopmentLogin,
    IssueResolve,
    SubjectSelectionCreate,
    TelegramLogin,
    TelegramUserSync,
    UserRoleUpdate,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    init_database()
    yield


app = FastAPI(title="Timetable Lens API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_document_or_404(document_id: uuid.UUID, session: Session) -> Document:
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


def require_bot_token(x_bot_token: str = Header(default="")) -> None:
    if not secrets.compare_digest(x_bot_token, settings.bot_service_token):
        raise HTTPException(status_code=401, detail="Invalid bot service token")


def user_payload(user: TelegramUser, include_subjects: bool = False) -> dict:
    payload = {
        "id": str(user.id),
        "telegramUserId": user.telegram_user_id,
        "username": user.username,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "languageCode": user.language_code,
        "role": user.role,
        "isActive": user.is_active,
        "notificationsEnabled": user.notifications_enabled,
        "createdAt": user.created_at.isoformat(),
        "lastSeenAt": user.last_seen_at.isoformat(),
        "subjectCount": len(user.subjects),
    }
    if include_subjects:
        payload["subjects"] = [subject_payload(subject) for subject in user.subjects]
    return payload


def current_dashboard_user(
    dashboard_session: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
) -> TelegramUser:
    if not dashboard_session:
        raise HTTPException(status_code=401, detail="Sign in required")
    token_hash = hashlib.sha256(dashboard_session.encode()).hexdigest()
    login = session.scalar(
        select(AdminSession)
        .where(AdminSession.token_hash == token_hash, AdminSession.expires_at > utcnow())
        .options(selectinload(AdminSession.user).selectinload(TelegramUser.subjects))
    )
    if not login or not login.user.is_active:
        raise HTTPException(status_code=401, detail="Session expired")
    return login.user


def require_reviewer(user: TelegramUser = Depends(current_dashboard_user)) -> TelegramUser:
    if user.role not in {"reviewer", "admin"}:
        raise HTTPException(status_code=403, detail="Reviewer access required")
    return user


def require_admin(user: TelegramUser = Depends(current_dashboard_user)) -> TelegramUser:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user


def get_telegram_user_or_404(telegram_user_id: int, session: Session) -> TelegramUser:
    user = session.scalar(
        select(TelegramUser)
        .where(TelegramUser.telegram_user_id == telegram_user_id)
        .options(selectinload(TelegramUser.subjects))
    )
    if not user:
        raise HTTPException(status_code=404, detail="Telegram user not found")
    return user


def subject_payload(subject: UserSubject) -> dict:
    return {
        "id": str(subject.id),
        "course": subject.course,
        "subCode": subject.subject_code,
    }


def document_payload(document: Document) -> dict:
    return {
        "id": str(document.id),
        "filename": document.original_filename,
        "sizeBytes": document.size_bytes,
        "status": document.status,
        "isActive": document.is_active,
        "stage": document.stage,
        "pageCount": document.page_count,
        "pagesProcessed": document.pages_processed,
        "recordsExtracted": document.records_extracted,
        "issuesFound": document.issues_found,
        "error": document.error,
        "createdAt": document.created_at.isoformat(),
        "completedAt": document.completed_at.isoformat() if document.completed_at else None,
    }


def build_schedule(sections: list[ScheduleSection]) -> list[dict]:
    schedule = []
    for section in sections:
        subjects = []
        for entry in sorted(section.entries, key=lambda item: (item.source_page, item.source_row)):
            subjects.append(
                {
                    "subCode": entry.sub_code,
                    "subName": entry.subject_name,
                    "lecturer": entry.lecturer,
                    "time": entry.time,
                    "room": entry.room,
                    "sessionType": entry.session_type,
                    "L": entry.session_type.upper().startswith("L"),
                    "T": entry.session_type.upper().startswith("T"),
                }
            )
        schedule.append({"course": section.course, "semester": section.semester, "subjects": subjects})
    return schedule


def load_document_sections(document_id: uuid.UUID, session: Session) -> list[ScheduleSection]:
    return list(
        session.scalars(
            select(ScheduleSection)
            .where(ScheduleSection.document_id == document_id)
            .options(selectinload(ScheduleSection.entries))
            .order_by(ScheduleSection.source_page)
        ).all()
    )


def entry_payload(entry: ScheduleEntry) -> dict:
    return {
        "id": str(entry.id),
        "sectionId": str(entry.section_id),
        "course": entry.section.course,
        "semester": entry.section.semester,
        "subCode": entry.sub_code,
        "subjectName": entry.subject_name,
        "sessionType": entry.session_type,
        "lecturer": entry.lecturer,
        "time": entry.time,
        "room": entry.room,
        "sourcePage": entry.source_page,
        "sourceRow": entry.source_row,
        "pageWidth": entry.page_width,
        "pageHeight": entry.page_height,
        "bbox": entry.bbox,
        "confidence": entry.confidence,
        "valid": entry.valid,
        "reviewed": entry.reviewed,
    }


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/auth/config")
def auth_config() -> dict:
    username = settings.telegram_bot_username
    if not username and settings.bot_token:
        try:
            with urlopen(
                f"https://api.telegram.org/bot{settings.bot_token}/getMe", timeout=5
            ) as response:
                result = json.load(response).get("result", {})
                username = result.get("username", "")
        except (OSError, URLError, ValueError, KeyError):
            username = ""
    return {"telegramBotUsername": username}


def create_dashboard_session(user: TelegramUser, response: Response, session: Session) -> None:
    raw_token = secrets.token_urlsafe(48)
    session.add(
        AdminSession(
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            user=user,
            expires_at=utcnow() + timedelta(days=settings.session_days),
        )
    )
    session.commit()
    response.set_cookie(
        "dashboard_session",
        raw_token,
        max_age=settings.session_days * 86400,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )


@app.post("/api/auth/development")
def development_login(
    payload: DevelopmentLogin,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
) -> dict:
    hostname = (request.url.hostname or "").lower()
    if settings.secure_cookies or hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise HTTPException(status_code=404, detail="Not found")
    if not secrets.compare_digest(payload.token, settings.bot_service_token):
        raise HTTPException(status_code=401, detail="Invalid development access token")
    user = session.scalar(
        select(TelegramUser)
        .where(TelegramUser.role == "admin", TelegramUser.is_active.is_(True))
        .options(selectinload(TelegramUser.subjects))
        .order_by(TelegramUser.created_at)
    )
    if not user:
        raise HTTPException(status_code=409, detail="No administrator has been configured")
    create_dashboard_session(user, response, session)
    return user_payload(user, include_subjects=True)


@app.post("/api/auth/telegram")
def telegram_login(
    payload: TelegramLogin,
    response: Response,
    session: Session = Depends(get_session),
) -> dict:
    if not settings.bot_token:
        raise HTTPException(status_code=503, detail="Telegram login is not configured")
    values = payload.model_dump(exclude={"hash"}, exclude_none=True)
    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hashlib.sha256(settings.bot_token.encode()).digest()
    expected_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected_hash, payload.hash):
        raise HTTPException(status_code=401, detail="Invalid Telegram signature")
    if abs(int(time.time()) - payload.auth_date) > 86400:
        raise HTTPException(status_code=401, detail="Telegram login has expired")

    user = session.scalar(
        select(TelegramUser)
        .where(TelegramUser.telegram_user_id == payload.id)
        .options(selectinload(TelegramUser.subjects))
    )
    if user is None:
        user = TelegramUser(
            telegram_user_id=payload.id,
            notification_chat_id=payload.id,
        )
        session.add(user)
    user.username = payload.username
    user.first_name = payload.first_name
    user.last_name = payload.last_name
    user.last_seen_at = utcnow()
    if payload.id in settings.administrator_ids:
        user.role = "admin"
    if user.role not in {"reviewer", "admin"} or not user.is_active:
        session.commit()
        raise HTTPException(status_code=403, detail="Dashboard access has not been granted")

    create_dashboard_session(user, response, session)
    return user_payload(user, include_subjects=True)


@app.get("/api/auth/me")
def auth_me(user: TelegramUser = Depends(require_reviewer)) -> dict:
    return user_payload(user, include_subjects=True)


@app.post("/api/auth/logout")
def logout(
    response: Response,
    dashboard_session: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
) -> dict:
    if dashboard_session:
        token_hash = hashlib.sha256(dashboard_session.encode()).hexdigest()
        login = session.scalar(select(AdminSession).where(AdminSession.token_hash == token_hash))
        if login:
            session.delete(login)
            session.commit()
    response.delete_cookie("dashboard_session", path="/")
    return {"signedOut": True}


@app.get("/api/users")
def list_users(
    _: TelegramUser = Depends(require_admin),
    session: Session = Depends(get_session),
) -> list[dict]:
    users = session.scalars(
        select(TelegramUser)
        .options(selectinload(TelegramUser.subjects))
        .order_by(TelegramUser.last_seen_at.desc())
    ).all()
    return [user_payload(user, include_subjects=True) for user in users]


@app.patch("/api/users/{user_id}/role")
def update_user_role(
    user_id: uuid.UUID,
    payload: UserRoleUpdate,
    administrator: TelegramUser = Depends(require_admin),
    session: Session = Depends(get_session),
) -> dict:
    user = session.scalar(
        select(TelegramUser)
        .where(TelegramUser.id == user_id)
        .options(selectinload(TelegramUser.subjects))
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == administrator.id and payload.role != "admin":
        raise HTTPException(status_code=409, detail="You cannot remove your own administrator role")
    user.role = payload.role
    session.commit()
    return user_payload(user, include_subjects=True)


@app.post("/api/bot/users/sync", dependencies=[Depends(require_bot_token)])
def sync_telegram_user(
    payload: TelegramUserSync, session: Session = Depends(get_session)
) -> dict:
    user = session.scalar(
        select(TelegramUser).where(
            TelegramUser.telegram_user_id == payload.telegram_user_id
        )
    )
    if user is None:
        user = TelegramUser(
            telegram_user_id=payload.telegram_user_id,
            notification_chat_id=payload.notification_chat_id,
        )
        session.add(user)
    if payload.telegram_user_id in settings.administrator_ids:
        user.role = "admin"
    user.notification_chat_id = payload.notification_chat_id
    user.username = payload.username
    user.first_name = payload.first_name
    user.last_name = payload.last_name
    user.language_code = payload.language_code
    user.last_seen_at = utcnow()
    user.is_active = True
    session.commit()
    return {
        "telegramUserId": user.telegram_user_id,
        "role": user.role,
        "isActive": user.is_active,
    }


@app.get(
    "/api/bot/users/{telegram_user_id}/subjects",
    dependencies=[Depends(require_bot_token)],
)
def list_user_subjects(
    telegram_user_id: int, session: Session = Depends(get_session)
) -> list[dict]:
    user = get_telegram_user_or_404(telegram_user_id, session)
    return [subject_payload(subject) for subject in sorted(user.subjects, key=lambda item: item.created_at)]


@app.post(
    "/api/bot/users/{telegram_user_id}/subjects",
    status_code=201,
    dependencies=[Depends(require_bot_token)],
)
def add_user_subject(
    telegram_user_id: int,
    payload: SubjectSelectionCreate,
    session: Session = Depends(get_session),
) -> dict:
    user = get_telegram_user_or_404(telegram_user_id, session)
    course = clean(payload.course)
    subject_code = clean(payload.subject_code).upper()
    existing = next(
        (
            subject
            for subject in user.subjects
            if subject.course == course and subject.subject_code == subject_code
        ),
        None,
    )
    if existing:
        raise HTTPException(status_code=409, detail="Subject is already selected")
    if len(user.subjects) >= 4:
        raise HTTPException(status_code=409, detail="Maximum of 4 subjects reached")
    subject = UserSubject(user=user, course=course, subject_code=subject_code)
    session.add(subject)
    session.commit()
    return subject_payload(subject)


@app.delete(
    "/api/bot/users/{telegram_user_id}/subjects/{subject_id}",
    dependencies=[Depends(require_bot_token)],
)
def remove_user_subject(
    telegram_user_id: int,
    subject_id: uuid.UUID,
    session: Session = Depends(get_session),
) -> dict:
    user = get_telegram_user_or_404(telegram_user_id, session)
    subject = next((item for item in user.subjects if item.id == subject_id), None)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject selection not found")
    session.delete(subject)
    session.commit()
    return {"removed": True}


@app.get("/api/bot/subscriptions", dependencies=[Depends(require_bot_token)])
def list_bot_subscriptions(session: Session = Depends(get_session)) -> list[dict]:
    users = session.scalars(
        select(TelegramUser)
        .where(
            TelegramUser.is_active.is_(True),
            TelegramUser.notifications_enabled.is_(True),
        )
        .options(selectinload(TelegramUser.subjects))
    ).all()
    return [
        {
            "telegramUserId": user.telegram_user_id,
            "chatId": user.notification_chat_id,
            "subjects": [subject_payload(subject) for subject in user.subjects],
        }
        for user in users
    ]


@app.get("/api/documents", dependencies=[Depends(require_reviewer)])
def list_documents(session: Session = Depends(get_session)) -> list[dict]:
    documents = session.scalars(select(Document).order_by(Document.created_at.desc())).all()
    return [document_payload(document) for document in documents]


@app.post("/api/documents", status_code=202, dependencies=[Depends(require_reviewer)])
async def upload_document(
    file: UploadFile = File(...), session: Session = Depends(get_session)
) -> dict:
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail="Only PDF files are accepted")

    document_id = uuid.uuid4()
    destination = settings.storage_dir / f"{document_id}.pdf"
    digest = hashlib.sha256()
    size = 0
    limit = settings.max_upload_mb * 1024 * 1024

    try:
        with destination.open("wb") as stream:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > limit:
                    raise HTTPException(
                        status_code=413, detail=f"PDF exceeds the {settings.max_upload_mb} MB limit"
                    )
                digest.update(chunk)
                stream.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    with destination.open("rb") as uploaded_pdf:
        signature = uploaded_pdf.read(5)
    if size < 5 or signature != b"%PDF-":
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF")

    document = Document(
        id=document_id,
        original_filename=Path(file.filename or "document.pdf").name,
        stored_path=str(destination),
        sha256=digest.hexdigest(),
        size_bytes=size,
    )
    session.add(document)
    session.commit()
    return document_payload(document)


@app.get("/api/documents/{document_id}", dependencies=[Depends(require_reviewer)])
def get_document(document_id: uuid.UUID, session: Session = Depends(get_session)) -> dict:
    return document_payload(get_document_or_404(document_id, session))


@app.get("/api/documents/{document_id}/file", dependencies=[Depends(require_reviewer)])
def get_document_file(document_id: uuid.UUID, session: Session = Depends(get_session)):
    document = get_document_or_404(document_id, session)
    return FileResponse(document.stored_path, media_type="application/pdf", filename=document.original_filename)


@app.get("/api/documents/{document_id}/entries", dependencies=[Depends(require_reviewer)])
def list_entries(document_id: uuid.UUID, session: Session = Depends(get_session)) -> list[dict]:
    get_document_or_404(document_id, session)
    statement = (
        select(ScheduleEntry)
        .join(ScheduleSection)
        .where(ScheduleSection.document_id == document_id)
        .options(selectinload(ScheduleEntry.section))
        .order_by(ScheduleEntry.source_page, ScheduleEntry.source_row)
    )
    return [entry_payload(entry) for entry in session.scalars(statement).all()]


@app.patch("/api/entries/{entry_id}", dependencies=[Depends(require_reviewer)])
def update_entry(
    entry_id: uuid.UUID, update: EntryUpdate, session: Session = Depends(get_session)
) -> dict:
    entry = session.scalar(
        select(ScheduleEntry)
        .where(ScheduleEntry.id == entry_id)
        .options(selectinload(ScheduleEntry.section))
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    values = {
        "sub_code": clean(update.sub_code).upper(),
        "subject_name": clean(update.subject_name),
        "session_type": clean(update.session_type).upper(),
        "lecturer": clean(update.lecturer),
        "time": clean(update.time).replace(" ", ""),
        "room": clean(update.room),
    }
    errors = validate(values)
    for key, value in values.items():
        setattr(entry, key, value)
    entry.valid = not errors
    entry.confidence = 1.0 if not errors else 0.5
    entry.reviewed = True
    session.execute(
        sql_update(ExtractionIssue)
        .where(ExtractionIssue.entry_id == entry.id)
        .values(status="resolved", corrected_data=values)
    )
    session.commit()
    return entry_payload(entry)


@app.get("/api/documents/{document_id}/issues", dependencies=[Depends(require_reviewer)])
def list_issues(document_id: uuid.UUID, session: Session = Depends(get_session)) -> list[dict]:
    get_document_or_404(document_id, session)
    issues = session.scalars(
        select(ExtractionIssue)
        .where(ExtractionIssue.document_id == document_id)
        .order_by(ExtractionIssue.page, ExtractionIssue.created_at)
    ).all()
    return [
        {
            "id": str(issue.id),
            "entryId": str(issue.entry_id) if issue.entry_id else None,
            "page": issue.page,
            "reason": issue.reason,
            "status": issue.status,
            "rawData": issue.raw_data,
            "correctedData": issue.corrected_data,
        }
        for issue in issues
    ]


@app.post("/api/issues/{issue_id}/resolve", dependencies=[Depends(require_reviewer)])
def resolve_issue(
    issue_id: uuid.UUID, resolution: IssueResolve, session: Session = Depends(get_session)
) -> dict:
    issue = session.get(ExtractionIssue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    issue.status = "resolved"
    issue.corrected_data = resolution.corrected_data
    session.commit()
    return {"id": str(issue.id), "status": issue.status}


@app.post(
    "/api/documents/{document_id}/retry",
    status_code=202,
    dependencies=[Depends(require_reviewer)],
)
def retry_document(document_id: uuid.UUID, session: Session = Depends(get_session)) -> dict:
    document = get_document_or_404(document_id, session)
    if document.status not in {"failed", "completed"}:
        raise HTTPException(status_code=409, detail="Document is already queued or processing")
    for section in list(document.sections):
        session.delete(section)
    for issue in list(document.issues):
        session.delete(issue)
    document.status = "queued"
    document.stage = "Waiting for a worker"
    document.pages_processed = 0
    document.records_extracted = 0
    document.issues_found = 0
    document.error = None
    document.completed_at = None
    document.is_active = False
    session.commit()
    return document_payload(document)


@app.post("/api/documents/{document_id}/activate", dependencies=[Depends(require_admin)])
def activate_document(document_id: uuid.UUID, session: Session = Depends(get_session)) -> dict:
    document = get_document_or_404(document_id, session)
    if document.status != "completed":
        raise HTTPException(status_code=409, detail="Only completed documents can be published")
    open_issues = session.scalar(
        select(func.count()).select_from(ExtractionIssue).where(
            ExtractionIssue.document_id == document_id, ExtractionIssue.status == "open"
        )
    )
    if open_issues:
        raise HTTPException(
            status_code=409,
            detail=f"Resolve {open_issues} open extraction issue(s) before publishing",
        )
    session.query(Document).filter(Document.is_active.is_(True)).update(
        {Document.is_active: False}, synchronize_session=False
    )
    document.is_active = True
    document.stage = "Published to Telegram bot"
    session.commit()
    return document_payload(document)


@app.get("/api/timetable")
def active_timetable(session: Session = Depends(get_session)) -> dict:
    document = session.scalar(select(Document).where(Document.is_active.is_(True)))
    if not document:
        raise HTTPException(status_code=404, detail="No timetable has been published yet")
    return {
        "document": document_payload(document),
        "schedule": build_schedule(load_document_sections(document.id, session)),
    }


@app.get("/api/documents/{document_id}/result", dependencies=[Depends(require_reviewer)])
def download_result(document_id: uuid.UUID, session: Session = Depends(get_session)):
    document = get_document_or_404(document_id, session)
    schedule = build_schedule(load_document_sections(document_id, session))

    response = JSONResponse({"schedule": schedule})
    stem = Path(document.original_filename).stem
    response.headers["Content-Disposition"] = f'attachment; filename="{stem}.json"'
    return response


@app.get("/api/documents/{document_id}/summary", dependencies=[Depends(require_reviewer)])
def document_summary(document_id: uuid.UUID, session: Session = Depends(get_session)) -> dict:
    get_document_or_404(document_id, session)
    open_issues = session.scalar(
        select(func.count()).select_from(ExtractionIssue).where(
            ExtractionIssue.document_id == document_id, ExtractionIssue.status == "open"
        )
    )
    courses = session.scalar(
        select(func.count()).select_from(ScheduleSection).where(ScheduleSection.document_id == document_id)
    )
    return {"openIssues": open_issues or 0, "courses": courses or 0}
