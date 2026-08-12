from telegram import Update
from telegram.ext import ContextTypes
from .constants import ADMIN_MAIN, ADMIN_SHIFTS, CB_HOME, CB_SHIFTS, CB_CALENDAR, CB_EDIT
from .keyboards import main_menu_keyboard, shifts_keyboard
from .utils import render


async def show_main(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id=None, notice=None) -> int:
    """Главное меню админа"""
    text = "🏠 Админ-панель\n\nВыберите раздел."
    if notice:
        text = f"{notice}\n\n{text}"
    await render(update, context, text, main_menu_keyboard(), message_id)
    return ADMIN_MAIN


async def show_shifts(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id=None, notice=None) -> int:
    """Показывает смены сегодня (перенаправляет в reports)"""
    from ..reports.handlers import show_day_report
    from utils.time_utils import today_msk_str
    today = today_msk_str()
    return await show_day_report(update, context, today, message_id, notice)


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает нажатия в главном меню"""
    query = update.callback_query
    await query.answer()
    data = query.data
    message_id = query.message.message_id if query.message else None

    if data == CB_HOME:
        return await show_main(update, context, message_id)

    if data == CB_SHIFTS:
        return await show_shifts(update, context, message_id)

    if data == CB_CALENDAR:
        from ..reports.handlers import show_calendar
        return await show_calendar(update, context, message_id)

    if data == CB_EDIT:
        from ..editor.handlers import show_edit_locations
        return await show_edit_locations(update, context, message_id)

    return await show_main(update, context, message_id)