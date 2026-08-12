import json
from datetime import datetime
from telegram.error import BadRequest
import logging
from db import get_connection
from db.checklist import get_items_for_location_and_day, get_shared_progress
from db.shifts import get_shifts_for_date
from .constants import (
    CATEGORY_ORDER, LOCATIONS, MSG_LIMIT, MONTHS_GEN,
)


logger = logging.getLogger(__name__)


def full_name(user: dict | None) -> str:
    if not user:
        return "Пользователь"
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
    return str(user.get("tg_id", "Пользователь"))


def progress_bar(done: int, total: int, size: int = 10) -> str:
    if total <= 0:
        return "▱" * size
    filled = round(size * done / total)
    filled = max(0, min(size, filled))
    return "▰" * filled + "▱" * (size - filled)


def percent(done: int, total: int) -> int:
    return int(done / total * 100) if total else 0


def format_date_ru(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{dt.day} {MONTHS_GEN[dt.month - 1]} {dt.year}"
    except Exception:
        return date_str


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


def get_shift_days_for_month(year: int, month: int) -> set[str]:
    start_date = f"{year:04d}-{month:02d}-01"
    end_date = f"{year + 1}-01-01" if month == 12 else f"{year:04d}-{month + 1:02d}-01"
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT date FROM shifts WHERE date >= ? AND date < ?",
            (start_date, end_date)
        ).fetchall()
        return {row["date"] for row in rows}


def get_day_report(date_str: str) -> dict:
    shifts = get_shifts_for_date(date_str)
    result = {
        "date": date_str,
        "bar": {"shifts": [], "items": [], "done": 0, "total": 0, "grouped": {}},
        "kitchen": {"shifts": [], "items": [], "done": 0, "total": 0, "grouped": {}},
    }

    for shift in shifts:
        loc = shift["location"]
        if loc in result:
            result[loc]["shifts"].append(shift)

    for loc_key in ["bar", "kitchen"]:
        items = get_items_for_location_and_day(loc_key, date_str)
        if not items:
            result[loc_key]["items"] = []
            continue

        shared_progress = get_shared_progress(loc_key, date_str)

        grouped = {}
        done = 0
        total = 0

        for item in items:
            item = dict(item)
            progress = shared_progress.get(item["id"])
            completed = progress.get("completed", 0) == 1 if progress else False
            item["completed"] = completed

            # Извлекаем медиа
            media_items = []
            if progress:
                if progress.get("photo_file_ids"):
                    try:
                        media_items = json.loads(progress["photo_file_ids"])
                        # Если это список строк (старый формат), преобразуем в объекты
                        if media_items and isinstance(media_items[0], str):
                            media_items = [{"type": "photo", "file_id": f} for f in media_items]
                    except:
                        media_items = []
                elif progress.get("photo_file_id"):
                    media_items = [{"type": "photo", "file_id": progress["photo_file_id"]}]
            item["media_items"] = media_items
            item["media_count"] = len(media_items)

            total += 1
            if completed:
                done += 1
            cat = item.get("category") or "weekly"
            grouped.setdefault(cat, []).append(item)

        result[loc_key]["items"] = items
        result[loc_key]["done"] = done
        result[loc_key]["total"] = total
        result[loc_key]["grouped"] = {cat: grouped[cat] for cat in CATEGORY_ORDER if cat in grouped}

    return result