# admin/menu/handlers.py

from telegram import Update
from telegram.ext import ContextTypes
from .constants import ADMIN_MAIN, ADMIN_SHIFTS, CB_HOME, CB_SHIFTS, CB_CALENDAR, CB_EDIT, CB_EMPLOYEES
from .keyboards import main_menu_keyboard, shifts_keyboard
from .utils import render, answer
from utils.time_utils import today_msk_str
from db.shifts import get_shifts_for_date  # предполагаем, что такая функция есть


async def show_main(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id=None, notice=None) -> int:
    """Главное меню админа"""
    text = "🏠 Админ-панель\n\nВыберите раздел."
    if notice:
        text = f"{notice}\n\n{text}"
    await render(update, context, text, main_menu_keyboard(), message_id)
    return ADMIN_MAIN


async def show_shifts_today(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id=None, notice=None) -> int:
    """Показывает смены на сегодня"""
    today = today_msk_str()
    shifts = get_shifts_for_date(today)  # функция должна возвращать список смен

    if not shifts:
        text = "📆 Сегодня смен нет."
    else:
        lines = ["📆 Смены на сегодня:"]
        for s in shifts:
            # s должно содержать: user_name, location, shift_name, start_time и т.д.
            lines.append(
                f"• {s.get('user_name', '—')} – {s.get('location', '—')} – "
                f"{s.get('shift_name', '—')} (с {s.get('start_time', '—')})"
            )
        text = "\n".join(lines)

    if notice:
        text = f"{notice}\n\n{text}"

    await render(update, context, text, shifts_keyboard(), message_id)
    return ADMIN_SHIFTS


async def show_report_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id=None, notice=None) -> int:
    """Открывает календарь для выбора даты и просмотра отчётов за неё"""
    # Импортируем функцию из модуля reports
    from ..reports.handlers import show_editor_calendar

    # Чтобы календарь открылся, нам нужен черновик. Создадим его для сегодня и типа "opening".
    # Это временный хак, чтобы использовать существующий календарь.
    # В идеале нужно создать отдельную функцию в reports, которая не требует черновика.
    from ..reports.utils import load_draft
    from utils.time_utils import today_msk_str

    today = today_msk_str()
    draft = load_draft(today, "opening")
    context.user_data["report_draft"] = draft
    context.user_data["report_type"] = "opening"
    context.user_data["report_date"] = today

    # Теперь вызываем календарь
    return await show_editor_calendar(update, context, message_id, notice)


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await answer(query)
    data = query.data
    message_id = query.message.message_id if query.message else None

    if data == CB_HOME:
        return await show_main(update, context, message_id)

    if data == CB_SHIFTS:
        return await show_shifts_today(update, context, message_id)

    if data == CB_CALENDAR:
        return await show_report_calendar(update, context, message_id)

    if data == CB_EDIT:
        from ..editor.handlers import show_edit_locations
        return await show_edit_locations(update, context, message_id)

    if data == CB_EMPLOYEES:
        from ..employees.handlers import show_employees_list
        return await show_employees_list(update, context, message_id)

    return await show_main(update, context, message_id)