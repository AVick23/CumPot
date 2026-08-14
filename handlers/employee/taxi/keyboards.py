from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .constants import CB_TAXI_ADD, CB_TAXI_HISTORY, CB_TAXI_BACK, CB_TAXI_CANCEL


def taxi_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Добавить расход", callback_data=CB_TAXI_ADD)],
        [InlineKeyboardButton("📋 История", callback_data=CB_TAXI_HISTORY)],
        [InlineKeyboardButton("◀️ Назад в меню", callback_data=CB_TAXI_BACK)],
    ])


def taxi_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✖️ Отмена", callback_data=CB_TAXI_CANCEL)]
    ])


def taxi_history_keyboard() -> InlineKeyboardMarkup:
    # Пока просто кнопка назад
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад", callback_data=CB_TAXI_BACK)]
    ])