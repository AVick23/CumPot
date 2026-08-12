import math
from datetime import datetime

from db import get_connection
from db.checklist import (
    get_all_items,
    add_checklist_item,
    update_checklist_item,
    delete_checklist_item as db_delete_item,
    get_items_for_location_and_day,
    get_shared_progress,
)
from db.shifts import get_shifts_for_date
from .constants import PAGE_SIZE, DAILY_CATEGORIES, CATEGORY_ORDER, MONTHS_GEN, LOCATIONS


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


def get_shift_days_for_month(year: int, month: int) -> set[str]:
    """Возвращает все даты месяца, когда были смены (любая локация)."""
    start_date = f"{year:04d}-{month:02d}-01"
    end_date = f"{year + 1}-01-01" if month == 12 else f"{year:04d}-{month + 1:02d}-01"
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT date FROM shifts WHERE date >= ? AND date < ?",
            (start_date, end_date)
        ).fetchall()
        return {row["date"] for row in rows}


def get_day_report(date_str: str) -> dict:
    """
    Возвращает отчёт за день:
    - смены (по локациям)
    - прогресс по каждой локации
    - сотрудники на смене
    """
    shifts = get_shifts_for_date(date_str)
    day_of_week = datetime.strptime(date_str, "%Y-%m-%d").weekday()
    result = {
        "date": date_str,
        "bar": {"shifts": [], "items": [], "done": 0, "total": 0, "grouped": {}},
        "kitchen": {"shifts": [], "items": [], "done": 0, "total": 0, "grouped": {}},
    }

    # Группируем смены по локации
    for shift in shifts:
        loc = shift["location"]
        if loc in result:
            result[loc]["shifts"].append(shift)

    # Для каждой локации загружаем чек-листы и прогресс
    for loc_key in ["bar", "kitchen"]:
        items = get_items_for_location_and_day(loc_key, day_of_week)
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
            item["has_photo"] = bool(progress and progress.get("photo_file_id"))
            item["photo_file_id"] = progress.get("photo_file_id") if progress else None

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
    counts = {key: 0 for key, _ in DAILY_CATEGORIES}
    counts["weekly"] = 0
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


def create_item(item_type: str, location: str, category: str, day_of_week: int | None, text: str) -> None:
    add_checklist_item(item_type, location, category, day_of_week, text.strip())


def update_item_text(item_id: int, text: str) -> None:
    update_checklist_item(item_id, text.strip())


def remove_item(item_id: int) -> None:
    db_delete_item(item_id)


def progress_bar(done: int, total: int, size: int = 10) -> str:
    if total <= 0:
        return "▱" * size
    filled = round(size * done / total)
    filled = max(0, min(size, filled))
    return "▰" * filled + "▱" * (size - filled)


def percent(done: int, total: int) -> int:
    return int(done / total * 100) if total else 0


def clip(text: str | None, limit: int = 35) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + "…"


def format_date_ru(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{dt.day} {MONTHS_GEN[dt.month - 1]} {dt.year}"
    except Exception:
        return date_str