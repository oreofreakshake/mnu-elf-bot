import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from .config import settings
from .database import SessionLocal, init_database
from .models import Document, ExtractionIssue, ScheduleEntry, ScheduleSection
from .parser import parse_pdf


def process(document_id) -> None:
    with SessionLocal() as session:
        document = session.get(Document, document_id)
        if not document:
            return
        active_document = document

        try:
            active_document.stage = "Reading table geometry"
            session.commit()

            def update_progress(page: int, total: int) -> None:
                active_document.page_count = total
                active_document.pages_processed = page
                active_document.stage = f"Extracting page {page} of {total}"
                session.commit()

            result = parse_pdf(Path(active_document.stored_path), update_progress)
            active_document.stage = "Validating extracted rows"
            session.commit()

            section_by_key: dict[str, ScheduleSection] = {}
            for parsed in result.sections:
                section = ScheduleSection(
                    document_id=active_document.id,
                    course=parsed.course,
                    title=parsed.title,
                    semester=parsed.semester,
                    source_page=parsed.source_page,
                )
                session.add(section)
                session.flush()
                section_by_key[parsed.key] = section

            issue_count = 0
            entry_count = 0
            for parsed in result.entries:
                section = section_by_key.get(parsed.section_key)
                if not section:
                    session.add(
                        ExtractionIssue(
                            document_id=active_document.id,
                            page=parsed.source_page,
                            reason="; ".join(parsed.errors),
                            raw_data=parsed.raw_data,
                        )
                    )
                    issue_count += 1
                    continue

                entry = ScheduleEntry(
                    section_id=section.id,
                    **parsed.values,
                    source_page=parsed.source_page,
                    source_row=parsed.source_row,
                    page_width=parsed.page_width,
                    page_height=parsed.page_height,
                    bbox=parsed.bbox,
                    raw_data=parsed.raw_data,
                    confidence=parsed.confidence,
                    valid=not parsed.errors,
                )
                session.add(entry)
                session.flush()
                entry_count += 1
                if parsed.errors:
                    session.add(
                        ExtractionIssue(
                            document_id=active_document.id,
                            entry_id=entry.id,
                            page=parsed.source_page,
                            reason="; ".join(parsed.errors),
                            raw_data=parsed.raw_data,
                        )
                    )
                    issue_count += 1

            for issue in result.page_issues:
                session.add(ExtractionIssue(document_id=active_document.id, **issue))
                issue_count += 1

            active_document.page_count = result.page_count
            active_document.pages_processed = result.page_count
            active_document.records_extracted = entry_count
            active_document.issues_found = issue_count
            active_document.status = "completed"
            active_document.stage = "Ready for review"
            active_document.completed_at = datetime.now(timezone.utc)
            session.commit()
        except Exception as exc:
            session.rollback()
            document = session.get(Document, document_id)
            if document:
                document.status = "failed"
                document.stage = "Processing failed"
                document.error = str(exc)[:2000]
                session.commit()


def claim_next_document():
    with SessionLocal() as session:
        document = session.scalar(
            select(Document)
            .where(Document.status == "queued")
            .order_by(Document.created_at)
            .with_for_update(skip_locked=True)
        )
        if not document:
            return None
        document.status = "processing"
        document.stage = "Starting parser"
        document_id = document.id
        session.commit()
        return document_id


def main() -> None:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    init_database()
    while True:
        document_id = claim_next_document()
        if document_id:
            process(document_id)
        else:
            time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    main()
