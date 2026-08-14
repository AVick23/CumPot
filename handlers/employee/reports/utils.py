import json
import logging
from datetime import datetime, timedelta

from telegram.error import BadRequest

try:
    from utils.time_utils import now_msk
except Exception:
    def now_msk():
        return datetime.now()

from db import get_connection
from db.users import get_user

from .constants import (
    MONTHS_GEN,
    MSG_LIMIT,
    REPORT_TYPE_LABELS,
)

logger = logging.getLogger(__name__)

_reports_table_ready = False


# =========================================================
# DB / TABLE
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


def format_report_preview(full_text: str, max_len: int = 700) -> str:
    full_text = full_text or ""

    if len(full_text) <= max_len:
        return full_text

    return full_text[:max_len].rstrip() + "…"


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
# REPORT PARSER
# =========================================================

def parse_report_sections(full_text: str, report_type: str) -> dict:
    sections = {}

    if report_type == "opening":
        markers = [
            "Влажность в помещении",
            "В эспрессо",
            "Тдс -",
            "Температура групп -",
            "Помол -",
            "Давление -",
            "Рецепт:",
            "В основе:",
            "В молоке:",
            "На фильтре:",
            "Стоп-лист",
        ]
    else:
        markers = [
            "Влажность в помещении",
            "Стопы",
            "Эспрессо, вода и заготовки по бару",
            "Рецепт по завершении:",
            "Заготовки бар:",
            "Рекомендации по фильтру:",
            "Еда",
            "Заготовки для еды:",
            "Блюда:",
            "Go-list",
            "График уборки / полив цветов",
            "Полы мылись",
            "Примечания:",
        ]

    lines = (full_text or "").split("\n")

    current_section = None
    buffer = []

    def match_marker(line: str):
        for marker in markers:
            variants = [marker, marker.rstrip(":")]

            for variant in variants:
                if variant and line.startswith(variant):
                    return marker, variant

        return None, None

    for line in lines:
        line = line.strip()

        if not line:
            continue

        marker, matched_variant = match_marker(line)

        if marker:
            if current_section and buffer:
                sections[current_section] = "\n".join(buffer).strip()

            current_section = marker.rstrip(":").strip()
            remainder = line[len(matched_variant):].lstrip(":").strip()

            buffer = [remainder] if remainder else []
        else:
            if current_section:
                buffer.append(line)

    if current_section and buffer:
        sections[current_section] = "\n".join(buffer).strip()

    return sections


# =========================================================
# DB OPERATIONS
# =========================================================

def save_report(date_str: str, report_type: str, author_id: int, full_text: str) -> int:
    _ensure_reports_table()

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


def get_last_report(report_type: str, before_date: str | None = None) -> dict | None:
    _ensure_reports_table()

    with get_connection() as conn:
        query = """
            SELECT id, date, report_type, author_id, full_text, parsed_data, created_at, updated_at
            FROM shift_reports
            WHERE report_type = ?
        """

        params = [report_type]

        if before_date:
            query += " AND date <= ?"
            params.append(before_date)

        query += " ORDER BY date DESC, id DESC LIMIT 1"

        row = conn.execute(query, tuple(params)).fetchone()

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


def get_previous_report(date_str: str, report_type: str) -> dict | None:
    try:
        prev_date = (
            datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=1)
        ).strftime("%Y-%m-%d")
    except Exception:
        return None

    return get_report(prev_date, report_type)


def get_previous_day_reports(date_str: str) -> dict:
    try:
        prev_date = (
            datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=1)
        ).strftime("%Y-%m-%d")
    except Exception:
        prev_date = None

    return {
        "date": prev_date,
        "opening": get_report(prev_date, "opening") if prev_date else None,
        "closing": get_report(prev_date, "closing") if prev_date else None,
    }


# =========================================================
# TEXT BUILDERS
# =========================================================

def build_report_summary_text(
    report: dict | None,
    date_str: str,
    report_type: str,
) -> str:
    type_label = REPORT_TYPE_LABELS.get(report_type, report_type)

    opening_exists = bool(get_report(date_str, "opening"))
    closing_exists = bool(get_report(date_str, "closing"))

    lines = [
        "📄 Отчёт",
        "",
        f"🗓 {format_date_ru(date_str)}",
        type_label,
        "",
        f"День: {'✅' if opening_exists else '⚪️'} Открытие · {'✅' if closing_exists else '⚪️'} Закрытие",
        "",
    ]

    if not report:
        lines.append("Статус: ⚪️ Не создан")
        lines.append("")
        lines.append("Создайте отчёт, когда будете готовы.")

        return "\n".join(lines)

    lines.append("Статус: ✅ Сохранён")

    author_name = "Сотрудник"

    if report.get("author_id"):
        author = get_user(report.get("author_id"))

        if author:
            author_name = full_name(author)

    lines.append(f"👤 Автор: {author_name}")

    updated_at = format_datetime_ru(report.get("updated_at"))

    if updated_at:
        lines.append(f"🕒 Обновлён: {updated_at}")

    parsed = safe_json(report.get("parsed_data"))

    if parsed:
        lines.append(f"🧩 Секций: {len(parsed)}")

    full_text = report.get("full_text") or ""

    lines.append(f"📏 Символов: {len(full_text)}")
    lines.append("")
    lines.append("Превью:")
    lines.append(format_report_preview(full_text, 300))

    return "\n".join(lines)