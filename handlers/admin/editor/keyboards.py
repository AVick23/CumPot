import calendar
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .constants import (
    CB_HOME, CB_TO_EDIT, CB_TO_CATEGORIES, CB_TO_ITEMS,
    CB_LOC_PREFIX, CB_CAT_PREFIX, CB_PAGE_PREFIX, CB_ITEM_PREFIX,
    CB_EDIT_ITEM_PREFIX, CB_DELETE_ITEM_PREFIX, CB_CONFIRM_DELETE_PREFIX,
    CB_ADD, CB_ADD_DAY_PREFIX, CB_CANCEL,
    CB_ITEM_TYPE_PREFIX, CB_DATE_PREFIX, CB_MONTH_PREV, CB_MONTH_NEXT,
    CB_HOUR_PREFIX, CB_MINUTE_PREFIX,
    CB_PHOTO_FLAG_PREFIX, CB_NOTIF_FLAG_PREFIX, CB_FLAGS_SKIP,
    CB_TOGGLE_PHOTO, CB_TOGGLE_NOTIFICATION, CB_CHANGE_TIME,
    CB_BACK_FROM_EDIT,
    LOCATIONS, DAILY_CATEGORIES, CATEGORY_LABELS, WEEKDAYS_SHORT, MONTHS,
)
from .utils import clip


# ---------- Основные клавиатуры редактора ----------
def edit_location_keyboard(counts: dict[str, int]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🍸 Бар · {counts.get('bar', 0)}", callback_data=f"{CB_LOC_PREFIX}:bar")],
        [InlineKeyboardButton(f"🍳 Кухня · {counts.get('kitchen', 0)}", callback_data=f"{CB_LOC_PREFIX}:kitchen")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data=CB_HOME)],
    ])


def edit_category_keyboard(location: str, counts: dict[str, int]) -> InlineKeyboardMarkup:
    rows = []
    for cat_key, cat_label in DAILY_CATEGORIES:
        rows.append([
            InlineKeyboardButton(f"{cat_label} · {counts.get(cat_key, 0)}",
                                 callback_data=f"{CB_CAT_PREFIX}:{location}:{cat_key}")
        ])
    rows.append([
        InlineKeyboardButton(f"{CATEGORY_LABELS['weekly']} · {counts.get('weekly', 0)}",
                             callback_data=f"{CB_CAT_PREFIX}:{location}:weekly")
    ])
    rows.append([
        InlineKeyboardButton("◀️ Локации", callback_data=CB_TO_EDIT),
        InlineKeyboardButton("🏠 Меню", callback_data=CB_HOME),
    ])
    return InlineKeyboardMarkup(rows)


def items_list_keyboard(location: str, category: str, page_items: list[dict],
                        page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows = []
    for item in page_items:
        indicators = ""
        if item.get("requires_photo"):
            indicators += "📸"
        if item.get("requires_notification"):
            indicators += "🔔"
        label = f"{clip(item.get('text'), 30)} {indicators}".strip()
        rows.append([
            InlineKeyboardButton(label, callback_data=f"{CB_ITEM_PREFIX}:{item['id']}")
        ])
    if total_pages > 1:
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"{CB_PAGE_PREFIX}:{location}:{category}:{page - 1}"))
        nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            nav_row.append(InlineKeyboardButton("➡️", callback_data=f"{CB_PAGE_PREFIX}:{location}:{category}:{page + 1}"))
        rows.append(nav_row)
    rows.append([InlineKeyboardButton("➕ Добавить пункт", callback_data=CB_ADD)])
    rows.append([
        InlineKeyboardButton("◀️ Категории", callback_data=CB_TO_CATEGORIES),
        InlineKeyboardButton("🏠 Меню", callback_data=CB_HOME),
    ])
    return InlineKeyboardMarkup(rows)


def item_detail_keyboard(item: dict) -> InlineKeyboardMarkup:
    item_id = item["id"]
    photo_status = "✅ Да" if item.get("requires_photo") else "❌ Нет"
    notif_status = "✅ Да" if item.get("requires_notification") else "❌ Нет"
    notif_time = item.get("notification_time") or "—"
    rows = [
        [InlineKeyboardButton("✏️ Изменить текст", callback_data=f"{CB_EDIT_ITEM_PREFIX}:{item_id}")],
        [InlineKeyboardButton(f"📸 Фото: {photo_status}", callback_data=f"{CB_TOGGLE_PHOTO}{item_id}")],
        [InlineKeyboardButton(f"🔔 Уведомление: {notif_status}", callback_data=f"{CB_TOGGLE_NOTIFICATION}{item_id}")],
    ]
    if item.get("requires_notification"):
        rows.append([
            InlineKeyboardButton(f"🕒 Время: {notif_time}", callback_data=f"{CB_CHANGE_TIME}{item_id}")
        ])
    rows.append([
        InlineKeyboardButton("🗑 Удалить", callback_data=f"{CB_DELETE_ITEM_PREFIX}:{item_id}"),
        InlineKeyboardButton("◀️ К списку", callback_data=CB_TO_ITEMS),
    ])
    return InlineKeyboardMarkup(rows)


def confirm_delete_keyboard(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"{CB_CONFIRM_DELETE_PREFIX}:{item_id}"),
            InlineKeyboardButton("✖️ Отмена", callback_data=f"{CB_ITEM_PREFIX}:{item_id}"),
        ]
    ])


def add_day_keyboard(selected_day: int | None = None) -> InlineKeyboardMarkup:
    rows = []
    row = []
    for i, day in enumerate(WEEKDAYS_SHORT):
        label = f"✅ {day}" if selected_day == i else day
        row.append(InlineKeyboardButton(label, callback_data=f"{CB_ADD_DAY_PREFIX}:{i}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([
        InlineKeyboardButton("◀️ Назад", callback_data=CB_TO_ITEMS),
        InlineKeyboardButton("✖️ Отмена", callback_data=CB_CANCEL),
    ])
    return InlineKeyboardMarkup(rows)


def text_prompt_keyboard(back_callback: str, cancel_callback: str | None = None) -> InlineKeyboardMarkup:
    row = [InlineKeyboardButton("◀️ Назад", callback_data=back_callback)]
    if cancel_callback and cancel_callback != back_callback:
        row.append(InlineKeyboardButton("✖️ Отмена", callback_data=cancel_callback))
    return InlineKeyboardMarkup([row])


# ---------- Клавиатуры для выбора типа ----------
def item_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Ежедневная", callback_data=f"{CB_ITEM_TYPE_PREFIX}daily")],
        [InlineKeyboardButton("📆 Недельная", callback_data=f"{CB_ITEM_TYPE_PREFIX}weekly")],
        [InlineKeyboardButton("📌 Одноразовая", callback_data=f"{CB_ITEM_TYPE_PREFIX}once")],
        [InlineKeyboardButton("◀️ Отмена", callback_data=CB_CANCEL)],
    ])


# ---------- Клавиатура календаря ----------
def calendar_keyboard(year: int, month: int, selected_date: str = None) -> InlineKeyboardMarkup:
    """Генерирует календарь на месяц с возможностью выбора дня."""
    rows = []
    # Заголовок с месяцем и годом + навигация
    rows.append([
        InlineKeyboardButton("◀️", callback_data=CB_MONTH_PREV),
        InlineKeyboardButton(f"{MONTHS[month - 1]} {year}", callback_data="noop"),
        InlineKeyboardButton("▶️", callback_data=CB_MONTH_NEXT),
    ])
    # Дни недели
    rows.append([InlineKeyboardButton(day, callback_data="noop") for day in WEEKDAYS_SHORT])

    first_weekday = datetime(year, month, 1).weekday()
    _, days_in_month = calendar.monthrange(year, month)

    row = []
    # Пустые ячейки до первого дня
    for _ in range(first_weekday):
        row.append(InlineKeyboardButton(" ", callback_data="noop"))

    for day in range(1, days_in_month + 1):
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        # Если дата совпадает с выбранной, помечаем
        label = f"✅ {day}" if date_str == selected_date else str(day)
        row.append(InlineKeyboardButton(label, callback_data=f"{CB_DATE_PREFIX}{date_str}"))
        if len(row) == 7:
            rows.append(row)
            row = []
    if row:
        while len(row) < 7:
            row.append(InlineKeyboardButton(" ", callback_data="noop"))
        rows.append(row)

    rows.append([InlineKeyboardButton("◀️ Назад", callback_data=CB_CANCEL)])
    return InlineKeyboardMarkup(rows)


# ---------- Клавиатуры выбора времени ----------
def hour_keyboard(selected_hour: int = None) -> InlineKeyboardMarkup:
    """Выбор часа (0-23) в виде сетки 4x6."""
    rows = []
    row = []
    for h in range(24):
        label = f"✅ {h:02d}" if selected_hour == h else f"{h:02d}"
        row.append(InlineKeyboardButton(label, callback_data=f"{CB_HOUR_PREFIX}{h}"))
        if len(row) == 6:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("◀️ Назад", callback_data=CB_CANCEL)])
    return InlineKeyboardMarkup(rows)


def minute_keyboard(selected_minute: int = None) -> InlineKeyboardMarkup:
    """Выбор минут (0,5,10,...55) в виде сетки 4x3."""
    rows = []
    row = []
    for m in range(0, 60, 5):
        label = f"✅ {m:02d}" if selected_minute == m else f"{m:02d}"
        row.append(InlineKeyboardButton(label, callback_data=f"{CB_MINUTE_PREFIX}{m}"))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("◀️ Назад", callback_data=CB_CANCEL)])
    return InlineKeyboardMarkup(rows)


# ---------- Клавиатуры для флагов ----------
def flag_photo_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Да", callback_data=f"{CB_PHOTO_FLAG_PREFIX}yes")],
        [InlineKeyboardButton("❌ Нет", callback_data=f"{CB_PHOTO_FLAG_PREFIX}no")],
        [InlineKeyboardButton("◀️ Назад", callback_data=CB_CANCEL)],
    ])


def flag_notification_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Да", callback_data=f"{CB_NOTIF_FLAG_PREFIX}yes")],
        [InlineKeyboardButton("❌ Нет", callback_data=f"{CB_NOTIF_FLAG_PREFIX}no")],
        [InlineKeyboardButton("◀️ Назад", callback_data=CB_CANCEL)],
    ])


def flags_skip_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭ Пропустить настройки флагов", callback_data=CB_FLAGS_SKIP)],
        [InlineKeyboardButton("◀️ Назад", callback_data=CB_CANCEL)],
    ])