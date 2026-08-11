import math
from datetime import datetime

from db import get_connection
from db.checklist import (
    get_all_items,
    add_checklist_item,
    update_checklist_item,
    delete_checklist_item as db_delete_item,
    get_items_for_location_and_day,
    get_progress_for_user_date,
)
from .constants import PAGE_SIZE, DAILY_CATEGORIES, CATEGORY_ORDER, MONTHS_GEN


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


def get_employees() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT tg_id, username, first_name, last_name, full_name
            FROM users
            WHERE is_admin = 0
            ORDER BY COALESCE(full_name, first_name, username)
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_user_by_id(user_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE tg_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def get_today_shifts_full() -> list[dict]:
    today = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                s.id,
                s.user_id,
                s.date,
                s.location,
                s.start_time,
                s.active,
                u.username,
                u.first_name,
                u.last_name,
                u.full_name
            FROM shifts s
            LEFT JOIN users u ON u.tg_id = s.user_id
            WHERE s.date = ?
            ORDER BY s.start_time
            """,
            (today,)
        ).fetchall()
        return [dict(row) for row in rows]


def get_employee_shift_days(employee_id: int, year: int, month: int) -> set[str]:
    start_date = f"{year:04d}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year:04d}-{month + 1:02d}-01"
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT date FROM shifts WHERE user_id = ? AND date >= ? AND date < ?",
            (employee_id, start_date, end_date)
        ).fetchall()
        return {row["date"] for row in rows}


def get_shift_for_date_any(user_id: int, date_str: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM shifts WHERE user_id = ? AND date = ? ORDER BY id DESC LIMIT 1",
            (user_id, date_str)
        ).fetchone()
        return dict(row) if row else None


def get_employee_progress(employee_id: int, date_str: str) -> dict | None:
    shift = get_shift_for_date_any(employee_id, date_str)
    if not shift:
        return None
    day_of_week = datetime.strptime(date_str, "%Y-%m-%d").weekday()
    items = get_items_for_location_and_day(shift["location"], day_of_week)
    progress = get_progress_for_user_date(employee_id, date_str)
    progress_dict = {p["item_id"]: p["completed"] for p in progress}

    grouped = {}
    done = 0
    total = 0
    for item in items:
        item = dict(item)
        completed = progress_dict.get(item["id"], 0) == 1
        item["completed"] = completed
        total += 1
        if completed:
            done += 1
        cat = item.get("category") or "weekly"
        grouped.setdefault(cat, []).append(item)

    ordered_grouped = {cat: grouped[cat] for cat in CATEGORY_ORDER if cat in grouped}
    return {"shift": shift, "grouped": ordered_grouped, "done": done, "total": total, "items": items}


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