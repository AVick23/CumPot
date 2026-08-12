from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .constants import (
    CB_HOME, CB_TO_EDIT, CB_TO_CATEGORIES, CB_TO_ITEMS,
    CB_LOC_PREFIX, CB_CAT_PREFIX, CB_PAGE_PREFIX, CB_ITEM_PREFIX,
    CB_EDIT_ITEM_PREFIX, CB_DELETE_ITEM_PREFIX, CB_CONFIRM_DELETE_PREFIX,
    CB_ADD, CB_ADD_DAY_PREFIX, CB_CANCEL,
    CB_ITEM_TYPE_PREFIX, CB_DUE_DATE_BACK, CB_PHOTO_FLAG_PREFIX,
    CB_NOTIF_FLAG_PREFIX, CB_FLAGS_SKIP,
    LOCATIONS, DAILY_CATEGORIES, CATEGORY_LABELS, WEEKDAYS_SHORT,
)
from ..utils import clip


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
        # Добавим индикаторы: 📸 - требует фото, 🔔 - требует уведомления
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


def item_detail_keyboard(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Изменить текст", callback_data=f"{CB_EDIT_ITEM_PREFIX}:{item_id}")],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"{CB_DELETE_ITEM_PREFIX}:{item_id}")],
        [InlineKeyboardButton("◀️ К списку", callback_data=CB_TO_ITEMS)],
    ])


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


# ---------- Новые клавиатуры для расширенного добавления ----------
def item_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Ежедневная", callback_data=f"{CB_ITEM_TYPE_PREFIX}daily")],
        [InlineKeyboardButton("📆 Недельная", callback_data=f"{CB_ITEM_TYPE_PREFIX}weekly")],
        [InlineKeyboardButton("📌 Одноразовая", callback_data=f"{CB_ITEM_TYPE_PREFIX}once")],
        [InlineKeyboardButton("◀️ Отмена", callback_data=CB_CANCEL)],
    ])


def flag_photo_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Да", callback_data=f"{CB_PHOTO_FLAG_PREFIX}yes")],
        [InlineKeyboardButton("❌ Нет", callback_data=f"{CB_PHOTO_FLAG_PREFIX}no")],
        [InlineKeyboardButton("◀️ Назад", callback_data=CB_DUE_DATE_BACK)],
    ])


def flag_notification_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Да", callback_data=f"{CB_NOTIF_FLAG_PREFIX}yes")],
        [InlineKeyboardButton("❌ Нет", callback_data=f"{CB_NOTIF_FLAG_PREFIX}no")],
        [InlineKeyboardButton("◀️ Назад", callback_data=CB_DUE_DATE_BACK)],
    ])


def flags_skip_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭ Пропустить настройки флагов", callback_data=CB_FLAGS_SKIP)],
        [InlineKeyboardButton("◀️ Назад", callback_data=CB_DUE_DATE_BACK)],
    ])