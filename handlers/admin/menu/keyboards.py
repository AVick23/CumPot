from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .constants import CB_SHIFTS, CB_CALENDAR, CB_EDIT, CB_HOME


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Смены сегодня", callback_data=CB_SHIFTS)],
        [InlineKeyboardButton("📊 Отчёт по дате", callback_data=CB_CALENDAR)],
        [InlineKeyboardButton("📝 Чек-листы", callback_data=CB_EDIT)],
    ])


def shifts_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Главное меню", callback_data=CB_HOME)]
    ])