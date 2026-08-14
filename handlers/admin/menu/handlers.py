from telegram import Update
from telegram.ext import ContextTypes
from .constants import ADMIN_MAIN, ADMIN_SHIFTS, CB_HOME, CB_SHIFTS, CB_CALENDAR, CB_EDIT, CB_EMPLOYEES
from .keyboards import main_menu_keyboard, shifts_keyboard
from .utils import render, answer
from utils.time_utils import today_msk_str
from db.shifts import get_shifts_for_date
from ..reports.handlers import show_calendar


async def show_main(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id=None, notice=None) -> int:
    """Главное меню админа"""
    text = "🏠 Админ-панель\n\nВыберите раздел."
    if notice:
        text = f"{notice}\n\n{text}"
    await render(update, context, text, main_menu_keyboard(), message_id)
    return ADMIN_MAIN


async def show_shifts(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id=None, notice=None) -> int:
    """Показывает смены на сегодня"""
    today = today_msk_str()
    shifts = get_shifts_for_date(today)

    if not shifts:
        text = "📆 Сегодня смен нет."
    else:
        lines = ["📆 Смены на сегодня:"]
        for s in shifts:
            lines.append(
                f"• {s.get('user_name', '—')} – {s.get('location', '—')} – "
                f"{s.get('shift_name', '—')} (с {s.get('start_time', '—')})"
            )
        text = "\n".join(lines)

    if notice:
        text = f"{notice}\n\n{text}"

    await render(update, context, text, shifts_keyboard(), message_id)
    return ADMIN_SHIFTS


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await answer(query)
    data = query.data
    message_id = query.message.message_id if query.message else None

    if data == CB_HOME:
        return await show_main(update, context, message_id)

    if data == CB_SHIFTS:
        return await show_shifts(update, context, message_id)

    if data == CB_CALENDAR:
        # Открываем календарь для выбора даты и просмотра отчётов
        return await show_calendar(update, context, message_id)

    if data == CB_EDIT:
        from ..editor.handlers import show_edit_locations
        return await show_edit_locations(update, context, message_id)

    if data == CB_EMPLOYEES:
        from ..employees.handlers import show_employees_list
        return await show_employees_list(update, context, message_id)

    return await show_main(update, context, message_id)