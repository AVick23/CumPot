import math
import logging
from datetime import datetime

from telegram.error import BadRequest

from db import get_connection

from .constants import (
    PAGE_SIZE,
    MSG_LIMIT,
    LOCATIONS,
    CATEGORY_LABELS,
    DAILY_CATEGORIES,
)

logger = logging.getLogger(__name__)

_SCHEMA_READY = False

_ALLOWED_UPDATE_FIELDS = {
    "type",
    "location",
    "category",
    "day_of_week",
    "days_of_week",
    "text",
    "requires_photo",
    "requires_notification",
    "notification_time",
    "due_date",
    "is_recurring",
    "sort_order",
}

_BOOL_FIELDS = {
    "requires_photo",
    "requires_notification",
    "is_recurring",
}


# =========================================================
# SCHEMA
# =========================================================

def _ensure_schema() -> None:
    """
    Мягко проверяет и создаёт таблицу checklist_items.
    """
    global _SCHEMA_READY

    if _SCHEMA_READY:
        return

    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS checklist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL DEFAULT 'daily',
                location TEXT NOT NULL,
                category TEXT NOT NULL,
                day_of_week INTEGER,
                days_of_week TEXT,
                text TEXT NOT NULL,
                requires_photo INTEGER DEFAULT 0,
                requires_notification INTEGER DEFAULT 0,
                notification_time TEXT,
                due_date TEXT,
                is_recurring INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0
            )
            """
        )

        cols = {row[1] for row in conn.execute("PRAGMA table_info(checklist_items)")}

        if "type" not in cols:
            conn.execute("ALTER TABLE checklist_items ADD COLUMN type TEXT DEFAULT 'daily'")

        if "day_of_week" not in cols:
            conn.execute("ALTER TABLE checklist_items ADD COLUMN day_of_week INTEGER")

        if "days_of_week" not in cols:
            conn.execute("ALTER TABLE checklist_items ADD COLUMN days_of_week TEXT")

        if "requires_photo" not in cols:
            conn.execute("ALTER TABLE checklist_items ADD COLUMN requires_photo INTEGER DEFAULT 0")

        if "requires_notification" not in cols:
            conn.execute("ALTER TABLE checklist_items ADD COLUMN requires_notification INTEGER DEFAULT 0")

        if "notification_time" not in cols:
            conn.execute("ALTER TABLE checklist_items ADD COLUMN notification_time TEXT")

        if "due_date" not in cols:
            conn.execute("ALTER TABLE checklist_items ADD COLUMN due_date TEXT")

        if "is_recurring" not in cols:
            conn.execute("ALTER TABLE checklist_items ADD COLUMN is_recurring INTEGER DEFAULT 1")

        if "sort_order" not in cols:
            conn.execute("ALTER TABLE checklist_items ADD COLUMN sort_order INTEGER DEFAULT 0")

        # Колонка created_at не используется – удаляем её создание, чтобы избежать ошибки SQLite
        # if "created_at" not in cols:
        #     conn.execute("ALTER TABLE checklist_items ADD COLUMN created_at TEXT")

    _SCHEMA_READY = True


# =========================================================
# TEXT / UI HELPERS
# =========================================================

def clip(text: str | None, limit: int = 35) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def truncate_text(text: str | None, limit: int = MSG_LIMIT) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def format_date_ru(date_str: str | None) -> str:
    if not date_str:
        return ""

    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%d.%m.%Y")
        except ValueError:
            continue

    return date_str


def format_date_short(date_str: str | None) -> str:
    if not date_str:
        return ""

    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%d.%m")
        except ValueError:
            continue

    return date_str


def parse_due_date(date_str: str | None) -> str | None:
    if not date_str:
        return None

    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


def type_for_category(category: str) -> str:
    """
    Упрощённая UX-логика:
    - opening/daytime/closing => daily
    - weekly => weekly
    - once => once
    """
    if category == "weekly":
        return "weekly"
    if category == "once":
        return "once"
    return "daily"


def get_week_days(item: dict) -> list[int]:
    """
    Возвращает список дней недели 0..6.
    Сначала смотрим days_of_week, потом старый day_of_week.
    """
    days: list[int] = []

    raw_days = item.get("days_of_week")
    if raw_days:
        for part in str(raw_days).split(","):
            part = part.strip()
            if part.isdigit():
                days.append(int(part))

    if not days and item.get("day_of_week") is not None:
        try:
            days = [int(item.get("day_of_week"))]
        except Exception:
            days = []

    return sorted(set(days))


def get_breadcrumb(location: str | None = None, category: str | None = None) -> str:
    if location and category:
        return f"{LOCATIONS.get(location, location)} · {CATEGORY_LABELS.get(category, category)}"

    if location:
        return LOCATIONS.get(location, location)

    if category:
        return CATEGORY_LABELS.get(category, category)

    return "Редактор"


# =========================================================
# RENDER
# =========================================================

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
# DB: READ
# =========================================================

def get_location_counts() -> dict[str, int]:
    _ensure_schema()

    counts = {"bar": 0, "kitchen": 0}

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT location, COUNT(*) AS cnt
            FROM checklist_items
            GROUP BY location
            """
        ).fetchall()

        for row in rows:
            loc = row["location"]
            if loc in counts:
                counts[loc] = row["cnt"]
            else:
                counts[loc] = row["cnt"]

    return counts


def get_category_counts(location: str) -> dict[str, int]:
    _ensure_schema()

    all_cats = [key for key, _ in DAILY_CATEGORIES] + ["weekly", "once"]
    counts = {key: 0 for key in all_cats}

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT category, COUNT(*) AS cnt
            FROM checklist_items
            WHERE location = ?
            GROUP BY category
            """,
            (location,),
        ).fetchall()

        for row in rows:
            cat = row["category"]
            if cat in counts:
                counts[cat] = row["cnt"]
            else:
                counts[cat] = row["cnt"]

    return counts


def get_items_for_editor(location: str, category: str) -> list[dict]:
    _ensure_schema()

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM checklist_items
            WHERE location = ? AND category = ?
            ORDER BY sort_order, id
            """,
            (location, category),
        ).fetchall()

    return [dict(row) for row in rows]


def paginate_items(items: list[dict], page: int) -> tuple[list[dict], int, int]:
    total_pages = max(1, math.ceil(len(items) / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    start = (page - 1) * PAGE_SIZE
    return items[start:start + PAGE_SIZE], total_pages, page


def get_item(item_id: int) -> dict | None:
    _ensure_schema()

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM checklist_items
            WHERE id = ?
            """,
            (item_id,),
        ).fetchone()

    return dict(row) if row else None


# =========================================================
# DB: WRITE
# =========================================================

def add_checklist_item(
    item_type: str,
    location: str,
    category: str,
    day_of_week: int | None,
    text: str,
    requires_photo: bool = False,
    requires_notification: bool = False,
    notification_time: str | None = None,
    due_date: str | None = None,
    is_recurring: bool = True,
    days_of_week: str | None = None,
) -> None:
    _ensure_schema()

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(MAX(sort_order), 0) + 1
            FROM checklist_items
            WHERE location = ? AND category = ?
            """,
            (location, category),
        ).fetchone()

        sort_order = row[0] if row else 1

        conn.execute(
            """
            INSERT INTO checklist_items (
                type,
                location,
                category,
                day_of_week,
                days_of_week,
                text,
                requires_photo,
                requires_notification,
                notification_time,
                due_date,
                is_recurring,
                sort_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item_type,
                location,
                category,
                day_of_week,
                days_of_week,
                text.strip(),
                1 if requires_photo else 0,
                1 if requires_notification else 0,
                notification_time,
                parse_due_date(due_date),
                1 if is_recurring else 0,
                sort_order,
            ),
        )


def update_checklist_item(item_id: int, **fields) -> None:
    _ensure_schema()

    if not fields:
        return

    sets = []
    vals = []

    for key, value in fields.items():
        if key not in _ALLOWED_UPDATE_FIELDS:
            continue

        if key in _BOOL_FIELDS and value is not None:
            value = 1 if value else 0

        if key == "due_date":
            value = parse_due_date(value)

        sets.append(f"{key} = ?")
        vals.append(value)

    if not sets:
        return

    vals.append(item_id)

    sql = f"""
        UPDATE checklist_items
        SET {', '.join(sets)}
        WHERE id = ?
    """

    with get_connection() as conn:
        conn.execute(sql, vals)


def delete_checklist_item(item_id: int) -> None:
    _ensure_schema()

    with get_connection() as conn:
        conn.execute(
            """
            DELETE FROM checklist_items
            WHERE id = ?
            """,
            (item_id,),
        )


# =========================================================
# DOMAIN WRAPPERS
# =========================================================

def create_item(
    item_type: str,
    location: str,
    category: str,
    day_of_week: int | None,
    text: str,
    requires_photo: bool = False,
    requires_notification: bool = False,
    notification_time: str | None = None,
    due_date: str | None = None,
    is_recurring: bool = True,
    days_of_week: str | None = None,
) -> None:
    add_checklist_item(
        item_type=item_type,
        location=location,
        category=category,
        day_of_week=day_of_week,
        text=text,
        requires_photo=requires_photo,
        requires_notification=requires_notification,
        notification_time=notification_time,
        due_date=due_date,
        is_recurring=is_recurring,
        days_of_week=days_of_week,
    )


def update_item_text(item_id: int, text: str) -> None:
    update_checklist_item(item_id, text=text.strip())


def update_item_flags(
    item_id: int,
    requires_photo: bool | None = None,
    requires_notification: bool | None = None,
    notification_time: str | None = None,
) -> None:
    kwargs = {}

    if requires_photo is not None:
        kwargs["requires_photo"] = requires_photo

    if requires_notification is not None:
        kwargs["requires_notification"] = requires_notification

    if notification_time is not None:
        kwargs["notification_time"] = notification_time

    if kwargs:
        update_checklist_item(item_id, **kwargs)


def update_item_days(item_id: int, days_of_week: str) -> None:
    """
    Обновляет дни недели для weekly-задачи.
    """
    normalized = []

    for part in str(days_of_week).split(","):
        part = part.strip()
        if part.isdigit():
            normalized.append(str(int(part)))

    normalized = sorted(set(normalized), key=int)
    days_str = ",".join(normalized) if normalized else None
    first_day = int(normalized[0]) if normalized else None

    update_checklist_item(
        item_id,
        days_of_week=days_str,
        day_of_week=first_day,
    )


def update_item_due_date(item_id: int, due_date: str) -> None:
    update_checklist_item(item_id, due_date=due_date)


def remove_item(item_id: int) -> None:
    delete_checklist_item(item_id)