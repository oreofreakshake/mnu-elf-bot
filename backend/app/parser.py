import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pdfplumber


CODE_RE = re.compile(r"^[A-Z]{2,6}\d{2,4}$")
SESSION_RE = re.compile(r"^(?:L|T|P)\d*$|^L/T$", re.IGNORECASE)
TIME_RE = re.compile(r"^(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)-\d{4}-\d{4}$|^TBD$", re.IGNORECASE)
SEMESTER_RE = re.compile(r"Semester\s+(\d+)", re.IGNORECASE)
DASHES = str.maketrans({"‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-"})


def clean(value: str | None) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFKC", value).translate(DASHES)
    return " ".join(value.replace("\u00a0", " ").split()).strip()


@dataclass
class ParsedSection:
    key: str
    course: str
    title: str
    semester: int
    source_page: int


@dataclass
class ParsedEntry:
    section_key: str
    values: dict
    source_page: int
    source_row: int
    page_width: float
    page_height: float
    bbox: dict
    raw_data: dict
    confidence: float
    errors: list[str]


@dataclass
class ParseResult:
    page_count: int
    sections: list[ParsedSection]
    entries: list[ParsedEntry]
    page_issues: list[dict]


def validate(values: dict) -> list[str]:
    errors: list[str] = []
    if not CODE_RE.fullmatch(values["sub_code"]):
        errors.append("Unrecognized subject code")
    if not values["subject_name"]:
        errors.append("Subject name is empty")
    if not SESSION_RE.fullmatch(values["session_type"]):
        errors.append("Unrecognized session type")
    if not values["lecturer"]:
        errors.append("Lecturer is empty")
    if not TIME_RE.fullmatch(values["time"]):
        errors.append("Time does not match Day-HHMM-HHMM or TBD")
    if not values["room"]:
        errors.append("Room is empty")
    return errors


def parse_pdf(path: Path, on_page: Callable[[int, int], None] | None = None) -> ParseResult:
    sections: list[ParsedSection] = []
    entries: list[ParsedEntry] = []
    page_issues: list[dict] = []
    current_title = ""
    current_course = ""
    current_semester = 0
    current_key = ""

    with pdfplumber.open(path) as pdf:
        total_pages = len(pdf.pages)
        for page_number, page in enumerate(pdf.pages, start=1):
            tables = page.find_tables()
            if not tables:
                page_issues.append(
                    {
                        "page": page_number,
                        "reason": "No native table detected; OCR review is required",
                        "raw_data": {"text_preview": clean(page.extract_text())[:500]},
                    }
                )
                if on_page:
                    on_page(page_number, total_pages)
                continue

            for table_index, table in enumerate(tables):
                rows = table.extract()
                for row_index, (row, geometry) in enumerate(zip(rows, table.rows, strict=False), start=1):
                    cells = [clean(cell) for cell in row]
                    nonempty = [cell for cell in cells if cell]
                    first = cells[0] if cells else ""

                    semester_match = SEMESTER_RE.search(first)
                    if len(nonempty) == 1 and semester_match:
                        current_title = first
                        current_semester = int(semester_match.group(1))
                        continue

                    if len(nonempty) == 1 and current_title and first.lower() != "updated final":
                        current_course = first
                        current_key = f"{page_number}:{table_index}:{row_index}:{current_course}"
                        sections.append(
                            ParsedSection(
                                key=current_key,
                                course=current_course,
                                title=current_title,
                                semester=current_semester,
                                source_page=page_number,
                            )
                        )
                        continue

                    if first.lower() in {"sub code", "subject code"}:
                        continue

                    if len(cells) < 6 or not first:
                        continue

                    values = {
                        "sub_code": first.upper(),
                        "subject_name": cells[1],
                        "session_type": cells[2].upper(),
                        "lecturer": cells[3],
                        "time": cells[4].replace(" ", ""),
                        "room": cells[5],
                    }
                    errors = validate(values)
                    if not current_key:
                        errors.append("Row was found before a course section")

                    x0, top, x1, bottom = geometry.bbox
                    entries.append(
                        ParsedEntry(
                            section_key=current_key,
                            values=values,
                            source_page=page_number,
                            source_row=row_index,
                            page_width=float(page.width),
                            page_height=float(page.height),
                            bbox={"x0": x0, "top": top, "x1": x1, "bottom": bottom},
                            raw_data={"cells": cells, "table": table_index},
                            confidence=1.0 if not errors else 0.5,
                            errors=errors,
                        )
                    )

            if on_page:
                on_page(page_number, total_pages)

    return ParseResult(total_pages, sections, entries, page_issues)

