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
from db.checklist import get_items_for_location_and_day, get_shared_progress
from db.shifts import get_shifts_for_date
from db.profile import get_taxi_expenses
from .constants import (
    CATEGORY_ORDER,
    CATEGORY_LABELS,
    LOCATIONS,
    MSG_LIMIT,
    MONTHS_GEN,
    WEEKDAYS_FULL,
    REPORT_MODE_SHORT,
    REPORT_MODE_FULL,
    PHOTO_PAGE_SIZE,
)

logger = logging.getLogger(__name__)


# ==========================================================
# TEXT HELPERS
# ==========================================================

def _clip(text: str | None, limit: int = 80) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


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
    if total <= 0:
        return 0
    return int(done / total * 100)


def format_date_ru(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{dt.day} {MONTHS_GEN[dt.month - 1]} {dt.year}"
    except Exception:
        return date_str


def format_weekday_ru(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return WEEKDAYS_FULL[dt.weekday()]
    except Exception:
        return ""


def truncate_text(text: str | None, limit: int = MSG_LIMIT) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


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


def paginate_list(items: list, page: int, page_size: int = PHOTO_PAGE_SIZE):
    items = items or []
    total_pages = max(1, (len(items) + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end], total_pages, page


# ==========================================================
# CALENDAR DATA
# ==========================================================

def get_shift_days_for_month(year: int, month: int) -> set[str]:
    start_date = f"{year:04d}-{month:02d}-01"
    end_date = (
        f"{year + 1}-01-01"
        if month == 12
        else f"{year:04d}-{month + 1:02d}-01"
    )
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT date
            FROM shifts
            WHERE date >= ? AND date < ?
            """,
            (start_date, end_date),
        ).fetchall()
    return {row["date"] for row in rows}


# ==========================================================
# MEDIA HELPERS
# ==========================================================

def _parse_media(raw) -> list[dict]:
    if not raw:
        return []
    data = raw
    if isinstance(data, str):
        data = data.strip()
        if not data:
            return []
        try:
            data = json.loads(data)
        except Exception:
            data = [x.strip() for x in data.split(",") if x.strip()]

    if isinstance(data, str):
        data = [data]
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return []

    result = []
    for entry in data:
        if isinstance(entry, str):
            entry = entry.strip()
            if entry:
                result.append({"type": "photo", "file_id": entry})
            continue
        if isinstance(entry, dict):
            file_id = (entry.get("file_id") or "").strip()
            if not file_id:
                continue
            media_item = dict(entry)
            media_item["file_id"] = file_id
            media_item.setdefault("type", "photo")
            result.append(media_item)
    return result


# ==========================================================
# DAY REPORT DATA (ЧЕК-ЛИСТЫ)
# ==========================================================

def get_day_report(date_str: str) -> dict:
    shifts = get_shifts_for_date(date_str)
    result = {
        "date": date_str,
        "bar": {
            "shifts": [], "items": [], "done": 0, "total": 0,
            "grouped": {}, "media_count": 0, "has_media": False,
        },
        "kitchen": {
            "shifts": [], "items": [], "done": 0, "total": 0,
            "grouped": {}, "media_count": 0, "has_media": False,
        },
    }

    for shift in shifts:
        loc = (shift.get("location") or "").strip()
        if loc in result:
            result[loc]["shifts"].append(shift)

    for loc_key in ["bar", "kitchen"]:
        items = get_items_for_location_and_day(loc_key, date_str)
        if not items:
            continue

        shared_progress = get_shared_progress(loc_key, date_str) or {}
        grouped = {}
        enriched_items = []
        done = 0
        total = 0
        media_count = 0

        for item in items:
            item_dict = dict(item)
            item_id = item_dict.get("id")
            progress = shared_progress.get(item_id)
            completed = bool(progress and progress.get("completed"))
            item_dict["completed"] = completed

            media_items = []
            if progress:
                media_items = _parse_media(progress.get("photo_file_ids"))
                if not media_items and progress.get("photo_file_id"):
                    media_items = [{"type": "photo", "file_id": progress.get("photo_file_id")}]

            item_dict["media_items"] = media_items
            item_dict["media_count"] = len(media_items)

            category = (item_dict.get("category") or "weekly").strip()
            item_dict["category"] = category

            total += 1
            media_count += len(media_items)
            if completed:
                done += 1

            grouped.setdefault(category, []).append(item_dict)
            enriched_items.append(item_dict)

        ordered_grouped = {}
        for cat in CATEGORY_ORDER:
            if cat in grouped:
                ordered_grouped[cat] = grouped[cat]
        for cat, cat_items in grouped.items():
            if cat not in ordered_grouped:
                ordered_grouped[cat] = cat_items

        result[loc_key].update({
            "items": enriched_items,
            "done": done,
            "total": total,
            "grouped": ordered_grouped,
            "media_count": media_count,
            "has_media": media_count > 0,
        })

    return result


# ==========================================================
# REPORT TEXT (ЧЕК-ЛИСТЫ)
# ==========================================================

def build_report_text(report: dict, mode: str = REPORT_MODE_SHORT):
    # Фото теперь учитываются всегда
    show_photos = True 
    
    date_str = report.get("date", "")
    header = f"📊 {format_date_ru(date_str)}"
    weekday = format_weekday_ru(date_str)
    if weekday:
        header += f" · {weekday}"

    lines = [header, ""]

    total_done = report["bar"]["done"] + report["kitchen"]["done"]
    total_all = report["bar"]["total"] + report["kitchen"]["total"]
    total_media = report["bar"]["media_count"] + report["kitchen"]["media_count"]

    if total_all > 0:
        lines.append(f"Итого: {total_done}/{total_all} · {percent(total_done, total_all)}%")
    else:
        lines.append("ℹ️ Задач нет")

    if show_photos and total_media > 0:
        lines.append(f"📸 Фото: {total_media}")

    lines.append("")

    has_bar_media = report["bar"]["has_media"]
    has_kitchen_media = report["kitchen"]["has_media"]

    for loc_key in ["bar", "kitchen"]:
        loc_data = report[loc_key]
        loc_label = LOCATIONS.get(loc_key, loc_key)
        shifts = loc_data["shifts"]
        grouped = loc_data["grouped"]
        done = loc_data["done"]
        total = loc_data["total"]
        loc_media_count = loc_data["media_count"]

        if mode == REPORT_MODE_FULL:
            lines.append(loc_label)
            if shifts:
                names = ", ".join(full_name(s) for s in shifts)
                lines.append(f"👥 Команда: {names}")
            else:
                lines.append("👤 Смен нет")

            if total > 0:
                lines.append(f"Прогресс: {progress_bar(done, total)} {done}/{total} · {percent(done, total)}%")
                if show_photos and loc_media_count > 0:
                    lines.append(f"📸 Фото: {loc_media_count}")
                lines.append("")

                for category, category_items in grouped.items():
                    category_label = CATEGORY_LABELS.get(category, category)
                    category_done = sum(1 for i in category_items if i.get("completed"))
                    lines.append(f"{category_label} · {category_done}/{len(category_items)}")
                    for item in category_items:
                        mark = "✅" if item.get("completed") else "⚪️"
                        text = _clip(item.get("text"), 70)
                        suffix = ""
                        if show_photos and item.get("media_count", 0) > 0:
                            suffix = f" · 🖼 {item['media_count']}"
                        lines.append(f"{mark} {text}{suffix}")
                    lines.append("")
            else:
                lines.append("📭 Чек-лист пуст")
                lines.append("")
        else:
            lines.append(loc_label)
            if shifts:
                names = ", ".join(full_name(s) for s in shifts)
                lines.append(f"👥 Смены: {len(shifts)} · {names}")
            else:
                lines.append("👤 Смен нет")

            if total > 0:
                lines.append(f"Прогресс: {done}/{total} · {percent(done, total)}%")
                left = total - done
                if left > 0:
                    lines.append(f"⏳ Осталось: {left}")
                if show_photos and loc_media_count > 0:
                    lines.append(f"📸 Фото: {loc_media_count}")
            else:
                lines.append("📭 Чек-лист пуст")
            lines.append("")

    text = "\n".join(lines).strip()
    return text, has_bar_media, has_kitchen_media


def get_report_text(date_str: str, mode: str):
    report = get_day_report(date_str)
    return build_report_text(report, mode)


# ==========================================================
# PHOTO REPORT DATA (ЧЕК-ЛИСТЫ)
# ==========================================================

def get_photo_overview(date_str: str) -> dict:
    report = get_day_report(date_str)
    bar_count = report["bar"]["media_count"]
    kitchen_count = report["kitchen"]["media_count"]
    return {
        "date": date_str,
        "bar": bar_count,
        "kitchen": kitchen_count,
        "total": bar_count + kitchen_count,
    }


def get_location_photo_menu(date_str: str, location: str) -> dict:
    report = get_day_report(date_str)
    loc_data = report.get(location) or {}
    items = loc_data.get("items", [])
    items_with_media = [item for item in items if item.get("media_count", 0) > 0]

    categories_raw = {}
    total_media = 0
    for item in items_with_media:
        category = (item.get("category") or "weekly").strip()
        media_count = item.get("media_count", 0)
        categories_raw.setdefault(category, {"media_count": 0, "task_count": 0})
        categories_raw[category]["media_count"] += media_count
        categories_raw[category]["task_count"] += 1
        total_media += media_count

    ordered_categories = {}
    for category in CATEGORY_ORDER:
        if category in categories_raw:
            ordered_categories[category] = categories_raw[category]
    for category, data in categories_raw.items():
        if category not in ordered_categories:
            ordered_categories[category] = data

    return {
        "date": date_str,
        "location": location,
        "total_media": total_media,
        "task_count": len(items_with_media),
        "categories": ordered_categories,
        "items": items_with_media,
    }


def get_category_photo_tasks(date_str: str, location: str, category: str) -> dict:
    menu = get_location_photo_menu(date_str, location)
    tasks = [
        item for item in menu.get("items", [])
        if (item.get("category") or "").strip() == category
    ]
    media_count = sum(item.get("media_count", 0) for item in tasks)
    return {
        "date": date_str,
        "location": location,
        "category": category,
        "tasks": tasks,
        "media_count": media_count,
        "task_count": len(tasks),
    }


def get_task_by_id_from_report(date_str: str, item_id: int):
    report = get_day_report(date_str)
    for loc_key in ["bar", "kitchen"]:
        for item in report[loc_key]["items"]:
            if item.get("id") == item_id:
                return item, loc_key
    return None, None


def build_task_media_caption(item: dict, location: str, date_str: str) -> str:
    location_label = LOCATIONS.get(location, location)
    category = (item.get("category") or "").strip()
    category_label = CATEGORY_LABELS.get(category, category)
    media_count = item.get("media_count", 0)

    user_name = None
    for media in item.get("media_items", []):
        if isinstance(media, dict) and media.get("user_name"):
            user_name = media.get("user_name")
            break

    lines = [
        "📌 Фото к задаче",
        "",
        item.get("text") or "",
        "",
        f"📍 {location_label}",
        f"📂 {category_label}",
        f"🗓 {format_date_ru(date_str)}",
        f"🖼 {media_count} шт.",
    ]
    if user_name:
        lines.append(f"👤 {user_name}")

    caption = "\n".join(lines)
    if len(caption) > 1024:
        caption = caption[:1023] + "…"
    return caption


# ==========================================================
# SHIFT REPORTS (СМЕННЫЕ ОТЧЁТЫ)
# ==========================================================

def get_shift_reports_for_date(date_str: str) -> dict:
    result = {"opening": None, "closing": None}
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, date, report_type, author_id, full_text, parsed_data, created_at, updated_at
            FROM shift_reports
            WHERE date = ?
            """,
            (date_str,),
        ).fetchall()
    for row in rows:
        report = dict(row)
        rtype = (report.get("report_type") or "").strip()
        if rtype in result:
            result[rtype] = report
    return result


def format_shift_report_text(report: dict | None) -> str:
    if not report:
        return "❌ Отчёт не сохранён"
    text = (report.get("full_text") or "").strip()
    if not text:
        return "⚠️ Отчёт пуст"
    return text


# ==========================================================
# TAXI (ТАКСИ) – данные и фото
# ==========================================================

def get_taxi_for_date(date_str: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT tg_id, full_name
            FROM users
            WHERE tg_id IN (
                SELECT DISTINCT user_id FROM taxi_expenses WHERE date = ?
            )
            ORDER BY full_name
            """,
            (date_str,),
        ).fetchall()
    users = [dict(row) for row in rows]

    result = []
    for user in users:
        expenses = get_taxi_expenses(user["tg_id"], date_str, date_str) or []
        total = sum(float(e.get("amount") or 0) for e in expenses)
        result.append({
            "user_id": user["tg_id"],
            "full_name": user.get("full_name") or "Сотрудник",
            "expenses": expenses,
            "total": total,
        })
    return result


def get_taxi_photo_overview(date_str: str) -> dict:
    taxi_data = get_taxi_for_date(date_str)
    users = []
    total_media = 0
    for user_data in taxi_data:
        media_items = []
        for exp in user_data.get("expenses", []):
            raw = exp.get("photo_file_ids") or exp.get("photo_file_id")
            if raw:
                media_items.extend(_parse_media(raw))
        if media_items:
            users.append({
                "user_id": user_data["user_id"],
                "full_name": user_data["full_name"],
                "media_items": media_items,
                "media_count": len(media_items),
            })
            total_media += len(media_items)

    return {
        "date": date_str,
        "users": users,
        "total_media": total_media,
    }