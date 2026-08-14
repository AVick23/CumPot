import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.time_utils import now_msk, today_msk_str
from db.users import get_user
from .constants import (
    REPORT_SELECT_TYPE,
    REPORT_VIEW_DATE,
    REPORT_VIEW_DETAIL,
    REPORT_AWAIT_TEXT,
    CB_REPORT_BACK_MENU,
    CB_REPORT_OPENING,
    CB_REPORT_CLOSING,
    CB_REPORT_DATE_PREFIX,
    CB_REPORT_PREV_MONTH,
    CB_REPORT_NEXT_MONTH,
    CB_REPORT_CREATE,
    CB_REPORT_VIEW,
    CB_REPORT_CANCEL,
    CB_REPORT_SAVE,
    REPORT_TYPE_LABELS,
    MSG_LIMIT,
)
from .keyboards import (
    report_type_keyboard,
    calendar_keyboard,
    report_action_keyboard,
    create_report_keyboard,
)
from .utils import (
    save_report,
    get_report,
    get_last_report,
    get_dates_with_reports,
    format_report_preview,
    truncate_text,
)

logger = logging.getLogger(__name__)

MAIN_MENU = 3  # из menu/constants.py


# =========================================================
# STATE HELPERS
# =========================================================

def set_state(context, state: int) -> int:
    context.user_data["state"] = state
    return state


def current_state(context) -> int:
    return context.user_data.get("state", MAIN_MENU)


async def render(update, context, text, reply_markup=None, message_id=None):
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id and message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
            )
            return message_id
        except Exception as e:
            logger.warning("Edit failed: %s", e)
    if chat_id:
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=truncate_text(text, MSG_LIMIT),
            reply_markup=reply_markup,
        )
        return msg.message_id
    return None


async def answer(query, text=None, show_alert=False):
    try:
        await query.answer(text or "", show_alert=show_alert)
    except Exception:
        pass


# =========================================================
# ENTRY POINT
# =========================================================

async def show_reports_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id=None, notice=None) -> int:
    """Показывает меню выбора типа отчёта."""
    text = "📋 Отчёты\n\nВыберите тип отчёта:"
    if notice:
        text = f"{notice}\n\n{text}"
    await render(update, context, text, report_type_keyboard(), message_id)
    return set_state(context, REPORT_SELECT_TYPE)


# =========================================================
# SELECT TYPE CALLBACK
# =========================================================

async def report_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    await answer(query)

    if data == CB_REPORT_BACK_MENU:
        from ..menu.handlers import show_main_menu
        return await show_main_menu(update, context, query.message.message_id)

    if data == CB_REPORT_OPENING or data == CB_REPORT_CLOSING:
        report_type = "opening" if data == CB_REPORT_OPENING else "closing"
        context.user_data["report_type"] = report_type
        # Переходим к календарю
        return await show_report_calendar(update, context, query.message.message_id)

    return await show_reports_menu(update, context, query.message.message_id)


# =========================================================
# CALENDAR
# =========================================================

async def show_report_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id=None, notice=None) -> int:
    now = now_msk()
    year = context.user_data.get("calendar_year", now.year)
    month = context.user_data.get("calendar_month", now.month)
    if not (1 <= month <= 12):
        month = now.month
    context.user_data["calendar_year"] = year
    context.user_data["calendar_month"] = month

    report_type = context.user_data.get("report_type", "opening")
    dates_with_reports = get_dates_with_reports(year, month, report_type)

    text = f"{REPORT_TYPE_LABELS[report_type]}\n\n{MONTHS[month-1]} {year}\n\nВыберите дату:"
    if notice:
        text = f"{notice}\n\n{text}"

    await render(update, context, text, calendar_keyboard(year, month, dates_with_reports), message_id)
    return set_state(context, REPORT_VIEW_DATE)


async def calendar_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    await answer(query)

    now = now_msk()
    year = context.user_data.get("calendar_year", now.year)
    month = context.user_data.get("calendar_month", now.month)

    if data == CB_REPORT_PREV_MONTH:
        if month == 1:
            month = 12
            year -= 1
        else:
            month -= 1
    elif data == CB_REPORT_NEXT_MONTH:
        if month == 12:
            month = 1
            year += 1
        else:
            month += 1
    else:
        return await show_report_calendar(update, context, query.message.message_id)

    context.user_data["calendar_year"] = year
    context.user_data["calendar_month"] = month
    return await show_report_calendar(update, context, query.message.message_id)


# =========================================================
# DATE SELECTION
# =========================================================

async def date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    await answer(query)

    prefix = CB_REPORT_DATE_PREFIX
    if not data.startswith(prefix):
        return await show_report_calendar(update, context, query.message.message_id)

    date_compact = data[len(prefix):]
    try:
        date_obj = datetime.strptime(date_compact, "%Y%m%d")
        date_str = date_obj.strftime("%Y-%m-%d")
    except:
        return await show_report_calendar(update, context, query.message.message_id)

    context.user_data["report_date"] = date_str
    report_type = context.user_data.get("report_type", "opening")
    report = get_report(date_str, report_type)

    # Показываем детали или действие
    return await show_report_detail(update, context, query.message.message_id, report)


async def show_report_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id=None, report=None) -> int:
    date_str = context.user_data.get("report_date")
    report_type = context.user_data.get("report_type", "opening")
    if not date_str:
        return await show_report_calendar(update, context, message_id)

    if report is None:
        report = get_report(date_str, report_type)

    if report:
        full_text = report["full_text"]
        preview = format_report_preview(full_text, 1000)  # покажем кусок
        text = f"📄 Отчёт за {date_str} ({REPORT_TYPE_LABELS[report_type]}):\n\n{preview}\n\n"
        kb = report_action_keyboard(date_str, report_type, has_report=True)
    else:
        # Нет отчёта за эту дату
        # Покажем пример из прошлого дня
        yesterday = (datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        example_report = get_last_report(report_type, before_date=yesterday)
        if example_report:
            example_text = example_report["full_text"]
            preview = format_report_preview(example_text, 500)
            text = f"📄 Отчёт за {date_str} ещё не создан.\n\nПример за {example_report['date']}:\n{preview}\n\nВы можете создать новый отчёт, отредактировав текст."
        else:
            text = f"📄 Отчёт за {date_str} ещё не создан.\n\nВы можете создать его сейчас."
        kb = report_action_keyboard(date_str, report_type, has_report=False)

    await render(update, context, text, kb, message_id)
    return set_state(context, REPORT_VIEW_DETAIL)


# =========================================================
# CREATE / EDIT REPORT
# =========================================================

async def create_report_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await answer(query)

    date_str = context.user_data.get("report_date")
    report_type = context.user_data.get("report_type", "opening")
    if not date_str:
        return await show_report_calendar(update, context, query.message.message_id)

    # Попробуем подставить пример из предыдущего дня
    yesterday = (datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    example_report = get_last_report(report_type, before_date=yesterday)
    if example_report:
        example_text = example_report["full_text"]
        prompt = f"📝 Создание отчёта за {date_str} ({REPORT_TYPE_LABELS[report_type]}).\n\nОтправьте текст отчёта. Вы можете использовать пример из {example_report['date']} как шаблон:\n\n{example_text}\n\nПросто скопируйте и отредактируйте."
    else:
        prompt = f"📝 Создание отчёта за {date_str} ({REPORT_TYPE_LABELS[report_type]}).\n\nОтправьте текст отчёта."

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✖️ Отмена", callback_data=CB_REPORT_CANCEL)]
    ])
    await render(update, context, prompt, kb, query.message.message_id)
    context.user_data["awaiting_report_text"] = True
    return set_state(context, REPORT_AWAIT_TEXT)


async def cancel_report_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await answer(query)
    context.user_data.pop("awaiting_report_text", None)
    date_str = context.user_data.get("report_date")
    if date_str:
        return await show_report_detail(update, context, query.message.message_id)
    return await show_report_calendar(update, context, query.message.message_id)


async def receive_report_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not context.user_data.get("awaiting_report_text"):
        # Если не ждём текст, просто проигнорируем
        return current_state(context)

    text = update.message.text
    if not text:
        await update.message.reply_text("Пожалуйста, отправьте текст отчёта.")
        return REPORT_AWAIT_TEXT

    date_str = context.user_data.get("report_date")
    report_type = context.user_data.get("report_type", "opening")
    user = update.effective_user
    if not user:
        await update.message.reply_text("Ошибка авторизации.")
        return MAIN_MENU

    # Сохраняем
    save_report(date_str, report_type, user.id, text)

    context.user_data.pop("awaiting_report_text", None)
    await update.message.reply_text("✅ Отчёт сохранён!")

    # Показываем обновлённый детальный вид
    # Создадим новое сообщение (не редактируем старое, т.к. оно уже было заменено)
    return await show_report_detail(update, context, message_id=None, report=None)


# =========================================================
# VIEW REPORT (показать полностью)
# =========================================================

async def view_report_full(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await answer(query)

    date_str = context.user_data.get("report_date")
    report_type = context.user_data.get("report_type", "opening")
    if not date_str:
        return await show_report_calendar(update, context, query.message.message_id)

    report = get_report(date_str, report_type)
    if not report:
        return await show_report_detail(update, context, query.message.message_id)

    full_text = report["full_text"]
    # Отправляем отдельным сообщением, т.к. оно может быть длинным
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text=full_text)

    # Возвращаемся к детальному виду
    return await show_report_detail(update, context, query.message.message_id)


# =========================================================
# MAIN CALLBACK ROUTER
# =========================================================

async def report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data

    if data == CB_REPORT_BACK_MENU:
        return await report_type_selection(update, context)

    if data in (CB_REPORT_OPENING, CB_REPORT_CLOSING):
        return await report_type_selection(update, context)

    if data in (CB_REPORT_PREV_MONTH, CB_REPORT_NEXT_MONTH):
        return await calendar_navigation(update, context)

    if data.startswith(CB_REPORT_DATE_PREFIX):
        return await date_selection(update, context)

    if data == CB_REPORT_CREATE:
        return await create_report_action(update, context)

    if data == CB_REPORT_VIEW:
        return await view_report_full(update, context)

    if data == CB_REPORT_CANCEL:
        return await cancel_report_creation(update, context)

    if data == CB_REPORT_SAVE:
        # Если пользователь нажал сохранить, но мы уже сохраняем при получении текста – оставляем для совместимости
        return current_state(context)

    return await show_reports_menu(update, context, query.message.message_id)