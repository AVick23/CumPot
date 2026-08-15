from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .constants import (
    CB_START_SHIFT, CB_CHECKLIST, CB_PROGRESS, CB_BACK_MENU,
    CB_POSITION_PREFIX, CB_SHIFT_TYPE_PREFIX, CB_PROFILE,
    CB_REPORTS, CB_REFERENCE   # ДОБАВЛЕНО
)


def position_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🍸 Бар", callback_data=f"{CB_POSITION_PREFIX}bar")],
        [InlineKeyboardButton("🍳 Кухня", callback_data=f"{CB_POSITION_PREFIX}kitchen")],
    ])


def main_menu_keyboard(has_shift: bool) -> InlineKeyboardMarkup:
    buttons = []

    if has_shift:
        buttons.append([InlineKeyboardButton("📋 Чек-лист", callback_data=CB_CHECKLIST)])
        buttons.append([InlineKeyboardButton("📊 Прогресс", callback_data=CB_PROGRESS)])
        buttons.append([InlineKeyboardButton("📋 Отчёты", callback_data=CB_REPORTS)])
    else:
        buttons.append([InlineKeyboardButton("🚀 Начать смену", callback_data=CB_START_SHIFT)])

    buttons.append([InlineKeyboardButton("👤 Мой профиль", callback_data=CB_PROFILE)])
    buttons.append([InlineKeyboardButton("📖 Справочник", callback_data=CB_REFERENCE)])   # ДОБАВЛЕНО

    return InlineKeyboardMarkup(buttons)


def back_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ В меню", callback_data=CB_BACK_MENU)]
    ])


def shift_types_keyboard(shift_types: list[dict]) -> InlineKeyboardMarkup:
    keyboard = []
    for st in shift_types:
        label = f"{st['name']} (с {st['start_time']})"
        keyboard.append([
            InlineKeyboardButton(label, callback_data=f"{CB_SHIFT_TYPE_PREFIX}{st['id']}")
        ])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data=CB_BACK_MENU)])
    return InlineKeyboardMarkup(keyboard)