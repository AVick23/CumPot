from datetime import datetime

from db.shifts import start_shift, get_active_shift, end_shift
from db.checklist import (
    get_items_for_location_and_day,
    save_progress,
    get_progress_for_user_date,
)
from db.users import get_user

from .constants import CATEGORY_ORDER, LOCATIONS


def get_position_label(position: str | None) -> str:
    return LOCATIONS.get(position, position or "—")


def start_shift_for_user(user_id: int) -> bool:
    """
    Начинает смену в позиции, которая сохранена в профиле сотрудника.
    """
    user = get_user(user_id)
    if not user:
        return False

    position = user.get("position")
    if position not in LOCATIONS:
        return False

    start_shift(user_id, position)
    return True


def get_current_shift(user_id: int) -> dict | None:
    return get_active_shift(user_id)


def end_current_shift(user_id: int) -> None:
    end_shift(user_id)


def get_checklist_items(user_id: int) -> list[dict] | None:
    """
    Возвращает задачи сотрудника на сегодня по активной смене.
    None — если нет активной смены.
    [] — если смена есть, но задач нет.
    """
    shift = get_active_shift(user_id)
    if not shift:
        return None

    location = shift["location"]
    day_of_week = datetime.now().weekday()
    date_str = datetime.now().strftime("%Y-%m-%d")

    items = get_items_for_location_and_day(location, day_of_week)
    if not items:
        return []

    progress = get_progress_for_user_date(user_id, date_str)
    progress_dict = {p["item_id"]: p["completed"] for p in progress}

    result = []
    for item in items:
        item = dict(item)
        item["completed"] = progress_dict.get(item["id"], 0) == 1
        result.append(item)

    return result


def get_categories_stats(user_id: int) -> dict[str, dict] | None:
    """
    Возвращает статистику по категориям:
    {
        "opening": {"done": 2, "total": 5},
        ...
    }
    """
    items = get_checklist_items(user_id)
    if items is None:
        return None

    stats: dict[str, dict] = {}

    for item in items:
        cat = item.get("category") or "weekly"

        if cat not in stats:
            stats[cat] = {"done": 0, "total": 0}

        stats[cat]["total"] += 1
        if item.get("completed"):
            stats[cat]["done"] += 1

    return stats


def get_items_by_category(user_id: int, category: str) -> list[dict] | None:
    items = get_checklist_items(user_id)
    if items is None:
        return None

    return [item for item in items if item.get("category") == category]


def get_item_by_id(user_id: int, item_id: int) -> dict | None:
    items = get_checklist_items(user_id)
    if items is None:
        return None

    for item in items:
        if item["id"] == item_id:
            return item

    return None


def toggle_item(user_id: int, item_id: int) -> bool | None:
    """
    Переключает статус задачи.
    Возвращает новый статус: True/False, либо None, если задача не найдена.
    """
    item = get_item_by_id(user_id, item_id)
    if item is None:
        return None

    new_state = not bool(item.get("completed"))
    save_progress(user_id, item_id, new_state)
    return new_state


def get_user_progress_summary(user_id: int) -> tuple[int, int, list[dict], dict[str, dict]] | None:
    """
    Возвращает:
    done, total, items, categories

    None — если нет активной смены.
    """
    items = get_checklist_items(user_id)
    if items is None:
        return None

    total = len(items)
    done = sum(1 for item in items if item.get("completed"))

    categories: dict[str, dict] = {}

    for item in items:
        cat = item.get("category") or "weekly"

        if cat not in categories:
            categories[cat] = {"done": 0, "total": 0}

        categories[cat]["total"] += 1
        if item.get("completed"):
            categories[cat]["done"] += 1

    ordered_categories = {
        cat: categories[cat]
        for cat in CATEGORY_ORDER
        if cat in categories
    }

    return done, total, items, ordered_categories


def progress_bar(done: int, total: int, size: int = 10) -> str:
    if total <= 0:
        return "▱" * size

    filled = round(size * done / total)
    filled = max(0, min(size, filled))

    return "▰" * filled + "▱" * (size - filled)


def percent(done: int, total: int) -> int:
    return int(done / total * 100) if total else 0