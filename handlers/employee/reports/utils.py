import json
import logging
from datetime import datetime

from telegram.error import BadRequest

try:
    from utils.time_utils import now_msk
except Exception:
    def now_msk():
        return datetime.now()

from db import get_connection
from db.users import get_user

from .constants import (
    MSG_LIMIT,
    MONTHS_GEN,
    REPORT_TYPES,
    REPORT_TYPE_LABELS,
    REPORT_SECTIONS,
    REPORT_SECTION_MARKERS,
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
# HELPERS
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


def format_datetime_ru(value: str | None) -> str:
    if not value:
        return ""

    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%d.%m %H:%M")
    except Exception:
        return value


def full_name(user: dict | None) -> str:
    if not user:
        return "Сотрудник"

    full = (user.get("full_name") or "").strip()

    if full:
        return full

    first = (user.get("first_name") or "").strip()
    last = (user.get("last_name") or "").strip()
    username = (user.get("username") or "").strip()

    name = " ".join([x for x in [first, last] if x]).strip()

    if name:
        return name

    if username:
        return f"@{username}"

    return str(user.get("tg_id", "Сотрудник"))


def safe_json(value: str | None) -> dict:
    if not value:
        return {}

    try:
        data = json.loads(value)

        if isinstance(data, dict):
            return data

        return {}
    except Exception:
        return {}


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


def get_last_report_before(date_str: str, report_type: str) -> dict | None:
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


def get_dates_with_reports(year: int, month: int, report_type: str | None = None) -> set[str]:
    _ensure_reports_table()

    start_date = f"{year:04d}-{month:02d}-01"

    if month == 12:
        end_date = f"{year + 1:04d}-01-01"
    else:
        end_date = f"{year:04d}-{month + 1:02d}-01"

    with get_connection() as conn:
        query = """
            SELECT DISTINCT date
            FROM shift_reports
            WHERE date >= ? AND date < ?
        """

        params = [start_date, end_date]

        if report_type:
            query += " AND report_type = ?"
            params.append(report_type)

        rows = conn.execute(query, tuple(params)).fetchall()

    return {row["date"] for row in rows}


# =========================================================
# PARSER / GENERATOR
# =========================================================

def _prefix_key(prefix: str) -> str:
    return prefix.rstrip(":").strip().rstrip("-").strip()


def _match_prefix(line: str, prefix: str) -> str | None:
    variants = [
        prefix,
        prefix.rstrip(":").strip(),
        prefix.rstrip(":").strip().rstrip("-").strip(),
    ]

    line_lower = line.lower()

    for variant in variants:
        if not variant:
            continue

        if line_lower.startswith(variant.lower()):
            return variant

    return None


def parse_report_sections(full_text: str, report_type: str) -> dict:
    sections = {}

    markers = REPORT_SECTION_MARKERS.get(report_type, [])

    current_key = None
    buffer = []

    for raw_line in (full_text or "").split("\n"):
        line = raw_line.strip()

        if not line:
            continue

        matched_prefix = None

        for prefix in markers:
            matched = _match_prefix(line, prefix)

            if matched:
                matched_prefix = matched
                key = _prefix_key(prefix)

                if current_key and buffer:
                    sections[current_key] = "\n".join(buffer).strip()

                current_key = key
                remainder = line[len(matched_prefix):].lstrip(":- ").strip()

                buffer = [remainder] if remainder else []

                break

        if not matched_prefix:
            if current_key:
                buffer.append(line)

    if current_key and buffer:
        sections[current_key] = "\n".join(buffer).strip()

    return sections


def build_full_text(report_type: str, values: dict) -> str:
    sections = REPORT_SECTIONS.get(report_type, [])
    markers = REPORT_SECTION_MARKERS.get(report_type, [])

    lines = []

    for index, section in enumerate(sections):
        prefix = markers[index] if index < len(markers) else f"{section}:"
        value = (values.get(section) or "").strip()

        if value:
            lines.append(f"{prefix} {value}".strip())
        else:
            lines.append(prefix)

    return "\n".join(lines)


# =========================================================
# DRAFT LOGIC
# =========================================================

def empty_draft(report_type: str) -> dict:
    sections = REPORT_SECTIONS.get(report_type, [])

    return {
        "order": sections,
        "values": {section: "" for section in sections},
        "raw": None,
        "source": "empty",
        "source_date": None,
    }


def draft_from_report(report: dict, report_type: str, source: str = "saved") -> dict:
    draft = empty_draft(report_type)

    parsed = safe_json(report.get("parsed_data"))

    if not parsed:
        parsed = parse_report_sections(report.get("full_text") or "", report_type)

    if parsed:
        for section in draft["order"]:
            draft["values"][section] = parsed.get(section, "") or ""

        draft["raw"] = None
    else:
        draft["raw"] = report.get("full_text") or ""

    draft["source"] = source
    draft["source_date"] = report.get("date")

    return draft


def draft_from_last_report(date_str: str, report_type: str) -> dict:
    last_report = get_last_report_before(date_str, report_type)

    if not last_report:
        return empty_draft(report_type)

    return draft_from_report(last_report, report_type, source="prev")


# =========================================================
# TEXT BUILDERS
# =========================================================

def build_dashboard_text(today: str, opening_report: dict | None, closing_report: dict | None) -> str:
    lines = [
        "📋 Отчёты",
        "",
        f"Сегодня, {format_date_ru(today)}",
        "",
    ]

    for report_type, report in [
        ("opening", opening_report),
        ("closing", closing_report),
    ]:
        label = REPORT_TYPE_LABELS.get(report_type, report_type)

        if not report:
            lines.append(f"{label}: ⚪️ не заполнен")
            continue

        updated_at = format_datetime_ru(report.get("updated_at"))
        author_name = ""

        if report.get("author_id"):
            author = get_user(report.get("author_id"))

            if author:
                author_name = full_name(author)

        status = f"{label}: ✅"

        if updated_at:
            status += f" {updated_at}"

        if author_name:
            status += f" · {author_name}"

        lines.append(status)

    lines.append("")
    lines.append("Нажмите, чтобы заполнить или изменить отчёт.")

    return "\n".join(lines)


def build_editor_text(draft: dict, date_str: str, report_type: str) -> str:
    type_label = REPORT_TYPE_LABELS.get(report_type, report_type)

    source = draft.get("source", "empty")
    source_date = draft.get("source_date")

    if source == "saved":
        source_label = "✅ Сохранённый отчёт"
    elif source == "prev" and source_date:
        source_label = f"📋 Черновик на основе отчёта за {format_date_ru(source_date)}"
    elif source == "text":
        source_label = "🧾 Текст обновлён"
    else:
        source_label = "🆕 Новый шаблон"

    lines = [
        type_label,
        f"🗓 {format_date_ru(date_str)}",
        source_label,
        "",
    ]

    raw = draft.get("raw")

    if raw:
        lines.append("⚠️ Разделы не распознаны.")
        lines.append("Можно сохранить как есть или отредактировать разделы ниже.")
        lines.append("")
        lines.append(truncate_text(raw, 500))
        lines.append("")
    else:
        order = draft.get("order", [])
        values = draft.get("values", {})

        filled = sum(1 for section in order if (values.get(section) or "").strip())

        lines.append(f"Заполнено: {filled}/{len(order)}")
        lines.append("")

        for index, section in enumerate(order, start=1):
            value = (values.get(section) or "").strip()
            preview = " ".join(value.split())

            if len(preview) > 70:
                preview = preview[:69] + "…"

            if not preview:
                preview = "—"

            lines.append(f"{index}. {section}: {preview}")

        lines.append("")

    lines.append("Нажмите на раздел, чтобы изменить его.")

    return "\n".join(lines)