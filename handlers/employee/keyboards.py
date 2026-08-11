from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .constants import (
    CB_START_SHIFT,
    CB_END_SHIFT,
    CB_CHECKLIST,
    CB_PROGRESS,
    CB_BACK_MENU,
    CB_BACK_CATEGORIES,
    CB_END_SHIFT_CONFIRM,
    CB_END_SHIFT_CANCEL,
    CB_POSITION_PREFIX,
    CB_CATEGORY_PREFIX,
    CB_ITEM_PREFIX,
    CB_TOGGLE_PREFIX,
    CATEGORY_NAMES,
    CATEGORY_ORDER,
)


def _clip(text: str | None, limit: int = 35) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + "…"


def position_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🍸 Бар", callback_data=f"{CB_POSITION_PREFIX}bar")],
        [InlineKeyboardButton("🍳 Кухня", callback_data=f"{CB_POSITION_PREFIX}kitchen")],
    ])


def main_menu_keyboard(has_shift: bool) -> InlineKeyboardMarkup:
    if has_shift:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Чек-лист", callback_data=CB_CHECKLIST)],
            [InlineKeyboardButton("📊 Прогресс", callback_data=CB_PROGRESS)],
            [InlineKeyboardButton("🏁 Завершить смену", callback_data=CB_END_SHIFT)],
        ])

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Начать смену", callback_data=CB_START_SHIFT)],
    ])


def back_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ В меню", callback_data=CB_BACK_MENU)]
    ])


def categories_keyboard(stats: dict[str, dict]) -> InlineKeyboardMarkup:
    rows = []

    for cat in CATEGORY_ORDER:
        if cat not in stats:
            continue

        item = stats[cat]
        if item.get("total", 0) <= 0:
            continue

        label = f"{CATEGORY_NAMES.get(cat, cat)} · {item['done']}/{item['total']}"
        rows.append([
            InlineKeyboardButton(label, callback_data=f"{CB_CATEGORY_PREFIX}{cat}")
        ])

    rows.append([InlineKeyboardButton("◀️ В меню", callback_data=CB_BACK_MENU)])
    return InlineKeyboardMarkup(rows)


def checklist_keyboard(items: list[dict]) -> InlineKeyboardMarkup:
    rows = []

    for item in items:
        status = "✅" if item.get("completed") else "⚪️"
        label = f"{status} {_clip(item.get('text'), 35)}"
        rows.append([
            InlineKeyboardButton(label, callback_data=f"{CB_ITEM_PREFIX}{item['id']}")
        ])

    rows.append([InlineKeyboardButton("◀️ Категории", callback_data=CB_BACK_CATEGORIES)])
    rows.append([InlineKeyboardButton("🏠 Меню", callback_data=CB_BACK_MENU)])

    return InlineKeyboardMarkup(rows)


def item_detail_keyboard(item_id: int, is_completed: bool) -> InlineKeyboardMarkup:
    toggle_label = "↩️ Отменить" if is_completed else "✅ Выполнить"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(toggle_label, callback_data=f"{CB_TOGGLE_PREFIX}{item_id}")],
        [InlineKeyboardButton("◀️ К списку", callback_data=CB_BACK_CATEGORIES)],
    ])


def progress_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ В меню", callback_data=CB_BACK_MENU)]
    ])


def end_shift_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Завершить", callback_data=CB_END_SHIFT_CONFIRM),
            InlineKeyboardButton("◀️ Отмена", callback_data=CB_END_SHIFT_CANCEL),
        ]
    ])