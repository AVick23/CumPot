from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .constants import (
    CB_START_SHIFT, CB_CHECKLIST, CB_PROGRESS, CB_BACK_MENU,
    CB_POSITION_PREFIX, CB_SHIFT_TYPE_PREFIX
)


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
            [InlineKeyboardButton("📋 Отчёты", callback_data="reports")],   # новая кнопка
        ])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Начать смену", callback_data=CB_START_SHIFT)],
    ])


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
    keyboard.append([
        InlineKeyboardButton("◀️ Назад", callback_data=CB_BACK_MENU)
    ])
    return InlineKeyboardMarkup(keyboard)