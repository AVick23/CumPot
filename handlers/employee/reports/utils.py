import json
import logging
from datetime import datetime

from telegram.error import BadRequest

try:
    from utils.time_utils import now_msk, today_msk_str
except Exception:
    def now_msk():
        return datetime.now()

    def today_msk_str():
        return datetime.now().strftime("%Y-%m-%d")

from db import get_connection

from .constants import (
    MSG_LIMIT,
    MONTHS_GEN,
    REPORT_SECTIONS,
    REPORT_SECTION_VARIANTS,
    REPORT_SECTION_OUTPUT_MARKERS,
)

logger = logging.getLogger(__name__)

_reports_table_ready = False


# =========================================================
# DB
# =========================================================

def _ensure_reports_table() -> None:
    global _reports_table_ready

    if _reports_table_ready:
        return

    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS shift_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                report_type TEXT NOT NULL,
                author_id INTEGER,
                full_text TEXT NOT NULL,
                parsed_data TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )

        cols = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(shift_reports)")
        }

        if "parsed_data" not in cols:
            conn.execute("ALTER TABLE shift_reports ADD COLUMN parsed_data TEXT")

        if "created_at" not in cols:
            conn.execute("ALTER TABLE shift_reports ADD COLUMN created_at TEXT")

        if "updated_at" not in cols:
            conn.execute("ALTER TABLE shift_reports ADD COLUMN updated_at TEXT")

        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_shift_reports_date_type
            ON shift_reports(date, report_type)
            """
        )

        conn.commit()

    _reports_table_ready = True


# =========================================================
# BASIC HELPERS
# =========================================================

def truncate_text(text: str | None, limit: int = MSG_LIMIT) -> str:
    text = text or ""

    if len(text) <= limit:
        return text

    return text[: limit - 1].rstrip() + "…"


def format_date_ru(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{dt.day} {MONTHS_GEN[dt.month - 1]} {dt.year}"
    except Exception:
        return date_str


async def render(update, context, text: str, reply_markup=None, message_id=None):
    text = truncate_text(text, MSG_LIMIT)
    chat_id = update.effective_chat.id if update.effective_chat else None

    if chat_id and message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
            )
            return message_id
        except BadRequest as e:
            if "Message is not modified" in str(e):
                return message_id
            logger.warning("Edit failed: %s", e)

    if chat_id:
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
        )
        return msg.message_id

    return None


async def send_long_message(context, chat_id: int, text: str, limit: int = 4000) -> None:
    text = text or ""

    if not text:
        return

    for start in range(0, len(text), limit):
        chunk = text[start:start + limit]

        await context.bot.send_message(
            chat_id=chat_id,
            text=chunk,
        )


# =========================================================
# REPORT DB OPERATIONS
# =========================================================

def save_report(
    date_str: str,
    report_type: str,
    author_id: int,
    full_text: str,
    parsed: dict | None = None,
) -> int:
    _ensure_reports_table()

    if parsed is None:
        parsed = parse_report_sections(full_text, report_type)

    parsed_json = json.dumps(parsed, ensure_ascii=False)
    now = now_msk().isoformat()

    with get_connection() as conn:
        existing = conn.execute(
            """
            SELECT id
            FROM shift_reports
            WHERE date = ? AND report_type = ?
            """,
            (date_str, report_type),
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE shift_reports
                SET full_text = ?, parsed_data = ?, updated_at = ?, author_id = ?
                WHERE id = ?
                """,
                (full_text, parsed_json, now, author_id, existing["id"]),
            )

            report_id = existing["id"]
        else:
            cur = conn.execute(
                """
                INSERT INTO shift_reports (
                    date,
                    report_type,
                    author_id,
                    full_text,
                    parsed_data,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (date_str, report_type, author_id, full_text, parsed_json, now, now),
            )

            report_id = cur.lastrowid

        conn.commit()

    logger.info("💾 Сохранён отчёт %s за %s (id=%s)", report_type, date_str, report_id)

    return report_id


def get_report(date_str: str, report_type: str) -> dict | None:
    _ensure_reports_table()

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, date, report_type, author_id, full_text, parsed_data, created_at, updated_at
            FROM shift_reports
            WHERE date = ? AND report_type = ?
            """,
            (date_str, report_type),
        ).fetchone()

    return dict(row) if row else None


def get_previous_report_of_type(date_str: str, report_type: str) -> dict | None:
    """
    Находит последний сохранённый отчёт указанного типа СТРОГО ДО указанной даты.
    Например, для закрытия 13.08 вернёт закрытие 12.08 (или 11.08), но НЕ открытие.
    """
    _ensure_reports_table()

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, date, report_type, author_id, full_text, parsed_data, created_at, updated_at
            FROM shift_reports
            WHERE report_type = ? AND date < ?
            ORDER BY date DESC, id DESC
            LIMIT 1
            """,
            (report_type, date_str),
        ).fetchone()

    return dict(row) if row else None


# =========================================================
# PARSER / GENERATOR
# =========================================================

def _clean_marker_remainder(remainder: str) -> str:
    remainder = (remainder or "").strip()

    if not remainder:
        return ""

    # Если после маркера остались только эмодзи/пунктуация — считаем, что значения нет.
    if all(not ch.isalnum() for ch in remainder):
        return ""

    return remainder.lstrip(":;-– ").strip()


def _match_section_key(line: str, report_type: str) -> tuple[str | None, str | None]:
    stripped = line.strip()

    if not stripped:
        return None, None

    sections = REPORT_SECTIONS.get(report_type, [])
    variants_map = REPORT_SECTION_VARIANTS.get(report_type, {})

    for section in sections:
        variants = variants_map.get(section, [])

        for variant in variants:
            if stripped.lower().startswith(variant.lower()):
                return section, variant

    return None, None


def parse_report_sections(full_text: str, report_type: str) -> dict:
    """
    Разбирает отчёт на:
    - _header: всё, что идёт до первого раздела;
    - значения разделов.
    """
    values = {
        "_header": "",
    }

    for section in REPORT_SECTIONS.get(report_type, []):
        values[section] = ""

    lines = (full_text or "").split("\n")

    header_lines = []
    current_key = None
    buffer = []
    started = False

    for line in lines:
        if not started:
            key, variant = _match_section_key(line, report_type)

            if key:
                started = True
                values["_header"] = "\n".join(header_lines).strip()

                current_key = key
                remainder = line[len(variant):] if variant else ""
                remainder = _clean_marker_remainder(remainder)

                buffer = [remainder] if remainder else []
            else:
                header_lines.append(line.rstrip())
        else:
            key, variant = _match_section_key(line, report_type)

            if key:
                if current_key:
                    values[current_key] = "\n".join(buffer).strip()

                current_key = key
                remainder = line[len(variant):] if variant else ""
                remainder = _clean_marker_remainder(remainder)

                buffer = [remainder] if remainder else []
            else:
                if current_key:
                    buffer.append(line.rstrip())

    if not started:
        return {
            "_header": (full_text or "").strip(),
        }

    if current_key:
        values[current_key] = "\n".join(buffer).strip()

    return values


def build_full_text(report_type: str, values: dict) -> str:
    parts = []

    header = (values.get("_header") or "").strip()

    if header:
        parts.append(header)

    sections = REPORT_SECTIONS.get(report_type, [])
    output_markers = REPORT_SECTION_OUTPUT_MARKERS.get(report_type, {})

    for section in sections:
        value = (values.get(section) or "").strip()

        if not value:
            continue

        marker = output_markers.get(section, section)

        if "\n" in value or len(value) > 60:
            parts.append(f"{marker}\n{value}".rstrip())
        else:
            parts.append(f"{marker} {value}".rstrip())

    return "\n\n".join(parts)


# =========================================================
# DRAFT LOGIC
# =========================================================

def auto_report_header(date_str: str, report_type: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        short_date = dt.strftime("%d.%m")
    except Exception:
        short_date = date_str

    if report_type == "opening":
        return f"Открытие {short_date}"

    return f"Закрытие {short_date}"


def empty_draft(date_str: str, report_type: str) -> dict:
    values = {
        "_header": auto_report_header(date_str, report_type),
    }

    for section in REPORT_SECTIONS.get(report_type, []):
        values[section] = ""

    return {
        "date": date_str,
        "type": report_type,
        "values": values,
        "raw": None,
        "source": "empty",
        "source_date": None,
    }


def draft_from_report(report: dict, report_type: str) -> dict:
    full_text = report.get("full_text") or ""

    values = parse_report_sections(full_text, report_type)

    return {
        "date": report.get("date"),
        "type": report_type,
        "values": values,
        "raw": full_text,
        "source": "saved",
        "source_date": report.get("date"),
    }


def draft_from_last(date_str: str, report_type: str) -> dict:
    last_report = get_previous_report_of_type(date_str, report_type)

    if not last_report:
        return empty_draft(date_str, report_type)

    values = parse_report_sections(last_report.get("full_text") or "", report_type)

    has_sections = any(
        (values.get(section) or "").strip()
        for section in REPORT_SECTIONS.get(report_type, [])
    )

    if not has_sections:
        return empty_draft(date_str, report_type)

    values["_header"] = auto_report_header(date_str, report_type)

    return {
        "date": date_str,
        "type": report_type,
        "values": values,
        "raw": None,
        "source": "prev",
        "source_date": last_report.get("date"),
    }


def load_draft(date_str: str, report_type: str) -> dict:
    existing = get_report(date_str, report_type)

    if existing:
        return draft_from_report(existing, report_type)

    return draft_from_last(date_str, report_type)


def draft_full_text(draft: dict) -> str:
    if draft.get("raw") is not None:
        return draft.get("raw") or ""

    return build_full_text(
        draft.get("type", "opening"),
        draft.get("values", {}),
    )