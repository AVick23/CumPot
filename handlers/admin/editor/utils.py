import math
import logging
from datetime import datetime
from telegram.error import BadRequest
from db import get_connection
from db.checklist import (
    get_all_items,
    add_checklist_item,
    update_checklist_item,
    delete_checklist_item as db_delete_item,
)
from .constants import PAGE_SIZE, DAILY_CATEGORIES, MSG_LIMIT, CATEGORY_LABELS

logger = logging.getLogger(__name__)


def clip(text: str | None, limit: int = 35) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + "…"


def truncate_text(text: str | None, limit: int = MSG_LIMIT) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + "…"


async def render(update, context, text, reply_markup=None, message_id=None):
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


def get_location_counts() -> dict[str, int]:
    counts = {"bar": 0, "kitchen": 0}
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT location, COUNT(*) AS cnt FROM checklist_items GROUP BY location"
        ).fetchall()
        for row in rows:
            counts[row["location"]] = row["cnt"]
    return counts


def get_category_counts(location: str) -> dict[str, int]:
    # добавляем "once"
    all_cats = [key for key, _ in DAILY_CATEGORIES] + ["weekly", "once"]
    counts = {key: 0 for key in all_cats}
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT category, COUNT(*) AS cnt FROM checklist_items WHERE location = ? GROUP BY category",
            (location,)
        ).fetchall()
        for row in rows:
            counts[row["category"]] = row["cnt"]
    return counts


def get_items_for_editor(location: str, category: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM checklist_items WHERE location = ? AND category = ? ORDER BY sort_order, id",
            (location, category)
        ).fetchall()
        return [dict(row) for row in rows]


def paginate_items(items: list[dict], page: int) -> tuple[list[dict], int, int]:
    total_pages = max(1, math.ceil(len(items) / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    start = (page - 1) * PAGE_SIZE
    return items[start:start + PAGE_SIZE], total_pages, page


def get_item(item_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM checklist_items WHERE id = ?", (item_id,)).fetchone()
        return dict(row) if row else None


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
    days_of_week: str | None = None   # новое поле
) -> None:
    add_checklist_item(
        item_type, location, category, day_of_week, text,
        requires_photo, requires_notification, notification_time,
        due_date, is_recurring, days_of_week
    )


def update_item_text(item_id: int, text: str) -> None:
    update_checklist_item(item_id, text=text.strip())


def update_item_flags(item_id: int, requires_photo: bool = None, requires_notification: bool = None, notification_time: str = None) -> None:
    kwargs = {}
    if requires_photo is not None:
        kwargs["requires_photo"] = 1 if requires_photo else 0
    if requires_notification is not None:
        kwargs["requires_notification"] = 1 if requires_notification else 0
    if notification_time is not None:
        kwargs["notification_time"] = notification_time
    if kwargs:
        update_checklist_item(item_id, **kwargs)


def update_item_days(item_id: int, days_of_week: str) -> None:
    """Обновляет дни недели для weekly задачи."""
    update_checklist_item(item_id, days_of_week=days_of_week)


def remove_item(item_id: int) -> None:
    db_delete_item(item_id)


def parse_due_date(date_str: str) -> str | None:
    try:
        for fmt in ("%d.%m.%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None
    except Exception:
        return None


def get_breadcrumb(location: str = None, category: str = None) -> str:
    parts = ["🏠 Главная"]
    if location:
        parts.append(LOCATIONS.get(location, location))
    if category:
        parts.append(CATEGORY_LABELS.get(category, category))
    return " → ".join(parts)