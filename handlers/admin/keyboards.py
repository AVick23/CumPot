import calendar
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .constants import (
    CB_NOOP,
    CB_HOME,
    CB_SHIFTS,
    CB_EMPLOYEES,
    CB_EDIT,
    CB_EMP_PREFIX,
    CB_PREV_MONTH,
    CB_NEXT_MONTH,
    CB_DAY_PREFIX,
    CB_TO_EMPLOYEES,
    CB_TO_CALENDAR,
    CB_TO_EDIT,
    CB_TO_CATEGORIES,
    CB_TO_ITEMS,
    CB_LOC_PREFIX,
    CB_CAT_PREFIX,
    CB_PAGE_PREFIX,
    CB_ITEM_PREFIX,
    CB_EDIT_ITEM_PREFIX,
    CB_DELETE_ITEM_PREFIX,
    CB_CONFIRM_DELETE_PREFIX,
    CB_ADD,
    CB_ADD_DAY_PREFIX,
    CB_CANCEL,
    LOCATIONS,
    DAILY_CATEGORIES,
    CATEGORY_LABELS,
    WEEKDAYS_SHORT,
    MONTHS,
)


def _clip(text: str | None, limit: int = 35) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + "…"


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Смены сегодня", callback_data=CB_SHIFTS)],
        [InlineKeyboardButton("👥 Сотрудники", callback_data=CB_EMPLOYEES)],
        [InlineKeyboardButton("📝 Чек-листы", callback_data=CB_EDIT)],
    ])


def back_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Главное меню", callback_data=CB_HOME)]
    ])


def shifts_keyboard() -> InlineKeyboardMarkup:
    return back_home_keyboard()


def employee_list_keyboard(employees: list[dict]) -> InlineKeyboardMarkup:
    rows = []

    for emp in employees:
        name = (emp.get("full_name") or "").strip()

        if not name:
            name = " ".join([emp.get("first_name") or "", emp.get("last_name") or ""]).strip()

        if not name:
            name = emp.get("username") or str(emp.get("tg_id"))

        rows.append([
            InlineKeyboardButton(
                _clip(name, 30),
                callback_data=f"{CB_EMP_PREFIX}{emp['tg_id']}"
            )
        ])

    rows.append([InlineKeyboardButton("🏠 Главное меню", callback_data=CB_HOME)])
    return InlineKeyboardMarkup(rows)


def calendar_keyboard(year: int, month: int, shift_days: set[str]) -> InlineKeyboardMarkup:
    rows = []

    rows.append([
        InlineKeyboardButton("◀️", callback_data=CB_PREV_MONTH),
        InlineKeyboardButton(f"{MONTHS[month - 1]} {year}", callback_data=CB_NOOP),
        InlineKeyboardButton("▶️", callback_data=CB_NEXT_MONTH),
    ])

    rows.append([
        InlineKeyboardButton(day, callback_data=CB_NOOP)
        for day in WEEKDAYS_SHORT
    ])

    first_weekday = datetime(year, month, 1).weekday()
    _, days_in_month = calendar.monthrange(year, month)

    row = []
    for _ in range(first_weekday):
        row.append(InlineKeyboardButton(" ", callback_data=CB_NOOP))

    for day in range(1, days_in_month + 1):
        date_db = f"{year:04d}-{month:02d}-{day:02d}"
        date_compact = f"{year:04d}{month:02d}{day:02d}"
        label = f"✅ {day}" if date_db in shift_days else str(day)

        row.append(InlineKeyboardButton(label, callback_data=f"{CB_DAY_PREFIX}{date_compact}"))

        if len(row) == 7:
            rows.append(row)
            row = []

    if row:
        while len(row) < 7:
            row.append(InlineKeyboardButton(" ", callback_data=CB_NOOP))
        rows.append(row)

    rows.append([
        InlineKeyboardButton("◀️ Сотрудники", callback_data=CB_TO_EMPLOYEES),
        InlineKeyboardButton("🏠 Меню", callback_data=CB_HOME),
    ])

    return InlineKeyboardMarkup(rows)


def day_progress_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Календарь", callback_data=CB_TO_CALENDAR)],
        [
            InlineKeyboardButton("👥 Сотрудники", callback_data=CB_TO_EMPLOYEES),
            InlineKeyboardButton("🏠 Меню", callback_data=CB_HOME),
        ],
    ])


def edit_location_keyboard(counts: dict[str, int]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🍸 Бар · {counts.get('bar', 0)}", callback_data=f"{CB_LOC_PREFIX}bar")],
        [InlineKeyboardButton(f"🍳 Кухня · {counts.get('kitchen', 0)}", callback_data=f"{CB_LOC_PREFIX}kitchen")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data=CB_HOME)],
    ])


def edit_category_keyboard(location: str, counts: dict[str, int]) -> InlineKeyboardMarkup:
    rows = []

    for cat_key, cat_label in DAILY_CATEGORIES:
        rows.append([
            InlineKeyboardButton(
                f"{cat_label} · {counts.get(cat_key, 0)}",
                callback_data=f"{CB_CAT_PREFIX}{location}:{cat_key}"
            )
        ])

    rows.append([
        InlineKeyboardButton(
            f"{CATEGORY_LABELS['weekly']} · {counts.get('weekly', 0)}",
            callback_data=f"{CB_CAT_PREFIX}{location}:weekly"
        )
    ])

    rows.append([
        InlineKeyboardButton("◀️ Локации", callback_data=CB_TO_EDIT),
        InlineKeyboardButton("🏠 Меню", callback_data=CB_HOME),
    ])

    return InlineKeyboardMarkup(rows)


def items_list_keyboard(
    location: str,
    category: str,
    page_items: list[dict],
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    rows = []

    for item in page_items:
        rows.append([
            InlineKeyboardButton(
                _clip(item.get("text"), 35),
                callback_data=f"{CB_ITEM_PREFIX}{item['id']}"
            )
        ])

    if total_pages > 1:
        nav_row = []
        if page > 1:
            nav_row.append(
                InlineKeyboardButton("⬅️", callback_data=f"{CB_PAGE_PREFIX}{location}:{category}:{page - 1}")
            )
        nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data=CB_NOOP))
        if page < total_pages:
            nav_row.append(
                InlineKeyboardButton("➡️", callback_data=f"{CB_PAGE_PREFIX}{location}:{category}:{page + 1}")
            )
        rows.append(nav_row)

    rows.append([InlineKeyboardButton("➕ Добавить пункт", callback_data=CB_ADD)])
    rows.append([
        InlineKeyboardButton("◀️ Категории", callback_data=CB_TO_CATEGORIES),
        InlineKeyboardButton("🏠 Меню", callback_data=CB_HOME),
    ])

    return InlineKeyboardMarkup(rows)


def item_detail_keyboard(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Изменить текст", callback_data=f"{CB_EDIT_ITEM_PREFIX}{item_id}")],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"{CB_DELETE_ITEM_PREFIX}{item_id}")],
        [InlineKeyboardButton("◀️ К списку", callback_data=CB_TO_ITEMS)],
    ])


def confirm_delete_keyboard(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"{CB_CONFIRM_DELETE_PREFIX}{item_id}"),
            InlineKeyboardButton("✖️ Отмена", callback_data=f"{CB_ITEM_PREFIX}{item_id}"),
        ]
    ])


def add_day_keyboard(selected_day: int | None = None) -> InlineKeyboardMarkup:
    rows = []
    row = []

    for i, day in enumerate(WEEKDAYS_SHORT):
        label = f"✅ {day}" if selected_day == i else day
        row.append(InlineKeyboardButton(label, callback_data=f"{CB_ADD_DAY_PREFIX}{i}"))
        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append([
        InlineKeyboardButton("◀️ К списку", callback_data=CB_TO_ITEMS),
        InlineKeyboardButton("✖️ Отмена", callback_data=CB_CANCEL),
    ])

    return InlineKeyboardMarkup(rows)


def text_prompt_keyboard(back_callback: str, cancel_callback: str | None = None) -> InlineKeyboardMarkup:
    row = [InlineKeyboardButton("◀️ Назад", callback_data=back_callback)]
    if cancel_callback and cancel_callback != back_callback:
        row.append(InlineKeyboardButton("✖️ Отмена", callback_data=cancel_callback))
    return InlineKeyboardMarkup([row])