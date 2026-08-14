import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

try:
    from utils.time_utils import now_msk
except Exception:
    def now_msk():
        return datetime.now()

from .constants import (
    REPORT_SELECT_TYPE,
    REPORT_VIEW_DATE,
    REPORT_VIEW_DETAIL,
    REPORT_AWAIT_TEXT,
    REPORT_CONFIRM_SAVE,
    CB_NOOP,
    CB_REPORT_BACK_MENU,
    CB_REPORT_TO_CALENDAR,
    CB_REPORT_TYPE_PREFIX,
    CB_REPORT_DATE_PREFIX,
    CB_REPORT_PREV_MONTH,
    CB_REPORT_NEXT_MONTH,
    CB_REPORT_CREATE,
    CB_REPORT_EDIT,
    CB_REPORT_VIEW,
    CB_REPORT_TEMPLATE,
    CB_REPORT_SAVE,
    CB_REPORT_REENTER,
    CB_REPORT_CANCEL,
    CB_REPORT_PREV_REPORT,
    MONTHS,
    REPORT_TYPE_LABELS,
    REPORT_TEMPLATES,
    REPORT_PREVIEW_LIMIT,
)

from .keyboards import (
    reports_calendar_keyboard,
    report_day_keyboard,
    report_create_keyboard,
    report_confirm_keyboard,
)

from .utils import (
    render,
    send_long_message,
    get_dates_with_reports,
    get_report,
    get_previous_report,
    save_report,
    format_date_ru,
    format_report_preview,
    build_report_summary_text,
)

MAIN_MENU = 3

logger = logging.getLogger(__name__)


# =========================================================
# HELPERS
# =========================================================

def _state(context: ContextTypes.DEFAULT_TYPE, state: int) -> int:
    context.user_data["state"] = state
    return state


def _current_state(context: ContextTypes.DEFAULT_TYPE) -> int:
    return context.user_data.get("state", MAIN_MENU)


async def _answer(query, text: str | None = None, show_alert: bool = False):
    try:
        await query.answer(text or "", show_alert=show_alert)
    except Exception:
        pass


def _get_report_type(context: ContextTypes.DEFAULT_TYPE) -> str:
    report_type = context.user_data.get("report_type", "opening")

    if report_type not in REPORT_TYPE_LABELS:
        report_type = "opening"

    return report_type


def _clear_draft(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("awaiting_report_text", None)
    context.user_data.pop("report_draft", None)


async def _go_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id=None):
    try:
        from ..menu.handlers import show_main_menu
        return await show_main_menu(update, context, message_id)
    except Exception:
        pass

    try:
        from ..menu.handlers import show_main
        return await show_main(update, context, message_id)
    except Exception:
        pass

    return await show_reports_menu(update, context, message_id)


# =========================================================
# CALENDAR SCREEN
# =========================================================

async def show_reports_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
    notice=None,
) -> int:
    user = update.effective_user

    if user:
        logger.info("📋 Пользователь %s открыл отчёты", user.id)

    now = now_msk()

    year = context.user_data.get("calendar_year", now.year)
    month = context.user_data.get("calendar_month", now.month)

    if not (1 <= month <= 12):
        month = now.month

    context.user_data["calendar_year"] = year
    context.user_data["calendar_month"] = month

    report_type = _get_report_type(context)
    context.user_data["report_type"] = report_type

    dates_with_reports = get_dates_with_reports(year, month, report_type)

    today = now.strftime("%Y-%m-%d")

    text = (
        "📋 Отчёты\n\n"
        f"{REPORT_TYPE_LABELS[report_type]}\n"
        f"{MONTHS[month - 1]} {year}\n\n"
        "📌 — отчёт сохранён\n"
        "• — сегодня\n\n"
        "Выберите день."
    )

    if notice:
        text = f"{notice}\n\n{text}"

    await render(
        update,
        context,
        text,
        reports_calendar_keyboard(
            report_type=report_type,
            year=year,
            month=month,
            dates_with_reports=dates_with_reports,
            today=today,
        ),
        message_id,
    )

    return _state(context, REPORT_VIEW_DATE)


# =========================================================
# DAY DETAIL SCREEN
# =========================================================

async def show_day_detail(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
    notice=None,
) -> int:
    date_str = context.user_data.get("report_date")
    report_type = _get_report_type(context)

    if not date_str:
        return await show_reports_menu(update, context, message_id)

    report = get_report(date_str, report_type)
    prev_report = get_previous_report(date_str, report_type)

    text = build_report_summary_text(report, date_str, report_type)

    if notice:
        text = f"{notice}\n\n{text}"

    kb = report_day_keyboard(
        has_report=bool(report),
        prev_exists=bool(prev_report),
    )

    await render(update, context, text, kb, message_id)

    logger.info(
        "📄 Пользователь открыл карточку отчёта: date=%s type=%s exists=%s",
        date_str,
        report_type,
        bool(report),
    )

    return _state(context, REPORT_VIEW_DETAIL)


# =========================================================
# CREATE / EDIT
# =========================================================

async def start_report_creation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
    edit: bool = False,
) -> int:
    date_str = context.user_data.get("report_date")
    report_type = _get_report_type(context)

    if not date_str:
        return await show_reports_menu(update, context, message_id)

    _clear_draft(context)

    context.user_data["awaiting_report_text"] = True

    title = "✏️ Изменение отчёта" if edit else "✏️ Новый отчёт"

    text = (
        f"{title}\n\n"
        f"{REPORT_TYPE_LABELS[report_type]} · {format_date_ru(date_str)}\n\n"
        "Отправьте текст отчёта одним сообщением.\n\n"
        "Если нужно, нажмите «🧾 Шаблон»."
    )

    if edit:
        text += "\n\n⚠️ Текущий отчёт будет заменён новым."

    await render(update, context, text, report_create_keyboard(), message_id)

    logger.info(
        "📝 Пользователь начал %s отчёта: date=%s type=%s",
        "изменение" if edit else "создание",
        date_str,
        report_type,
    )

    return _state(context, REPORT_AWAIT_TEXT)


async def send_report_template(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    await _answer(query)

    report_type = _get_report_type(context)
    template = REPORT_TEMPLATES.get(report_type, "")

    chat_id = update.effective_chat.id

    if chat_id and template:
        header = f"🧾 Шаблон: {REPORT_TYPE_LABELS.get(report_type, report_type)}\n\n"

        await send_long_message(context, chat_id, header + template)

        logger.info("🧾 Отправлен шаблон отчёта: type=%s", report_type)

    return _state(context, REPORT_AWAIT_TEXT)


async def receive_report_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user

    if not user:
        return MAIN_MENU

    awaiting = bool(context.user_data.get("awaiting_report_text"))
    draft_exists = bool(context.user_data.get("report_draft"))

    if not awaiting and not draft_exists:
        logger.warning("⚠️ Получен текст отчёта, но пользователь не в режиме редактирования")
        return _current_state(context)

    text = (update.message.text or "").strip() if update.message else ""

    if not text:
        await update.message.reply_text("⚠️ Отчёт не может быть пустым.")
        return _state(context, REPORT_AWAIT_TEXT)

    if len(text) > 4096:
        await update.message.reply_text("⚠️ Текст слишком длинный. Разбейте его на части.")
        return _state(context, REPORT_AWAIT_TEXT)

    context.user_data["report_draft"] = text
    context.user_data["awaiting_report_text"] = False

    logger.info(
        "📩 Получен текст отчёта от пользователя %s, длина=%s",
        user.id,
        len(text),
    )

    return await show_confirm_save(update, context)


async def show_confirm_save(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
) -> int:
    draft = context.user_data.get("report_draft")

    if not draft:
        return await start_report_creation(update, context, message_id)

    date_str = context.user_data.get("report_date")
    report_type = _get_report_type(context)

    preview = format_report_preview(draft, REPORT_PREVIEW_LIMIT)

    text = (
        "✅ Проверьте отчёт\n\n"
        f"{REPORT_TYPE_LABELS[report_type]} · {format_date_ru(date_str)}\n\n"
        f"{preview}\n\n"
        "Если всё верно, сохраните."
    )

    await render(update, context, text, report_confirm_keyboard(), message_id)

    logger.info("👀 Показан предпросмотр отчёта перед сохранением")

    return _state(context, REPORT_CONFIRM_SAVE)


async def save_report_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user

    if not user:
        return MAIN_MENU

    draft = context.user_data.get("report_draft")
    date_str = context.user_data.get("report_date")
    report_type = _get_report_type(context)

    if not draft or not date_str:
        return await show_reports_menu(update, context, notice="⚠️ Данные утеряны. Начните заново.")

    save_report(date_str, report_type, user.id, draft)

    _clear_draft(context)

    logger.info(
        "✅ Пользователь %s сохранил отчёт: date=%s type=%s",
        user.id,
        date_str,
        report_type,
    )

    return await show_day_detail(update, context, notice="✅ Отчёт сохранён.")


async def reenter_report_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("report_draft", None)
    context.user_data["awaiting_report_text"] = True

    date_str = context.user_data.get("report_date")
    report_type = _get_report_type(context)

    text = (
        "✏️ Введите текст заново\n\n"
        f"{REPORT_TYPE_LABELS[report_type]} · {format_date_ru(date_str)}\n\n"
        "Отправьте текст отчёта одним сообщением."
    )

    await render(update, context, text, report_create_keyboard())

    logger.info("🔁 Пользователь решил ввести текст отчёта заново")

    return _state(context, REPORT_AWAIT_TEXT)


async def cancel_report_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    _clear_draft(context)

    logger.info("❌ Пользователь отменил создание/изменение отчёта")

    return await show_day_detail(update, context, notice="Отменено.")


# =========================================================
# VIEW ACTIONS
# =========================================================

async def view_report_full(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    date_str = context.user_data.get("report_date")
    report_type = _get_report_type(context)

    if not date_str:
        return await show_reports_menu(update, context)

    report = get_report(date_str, report_type)

    if not report:
        return await show_day_detail(update, context, notice="⚠️ Отчёт не найден.")

    chat_id = update.effective_chat.id

    if not chat_id:
        return _state(context, REPORT_VIEW_DETAIL)

    header = (
        f"📄 {REPORT_TYPE_LABELS.get(report_type, report_type)}\n"
        f"🗓 {format_date_ru(date_str)}\n\n"
    )

    await send_long_message(context, chat_id, header + (report.get("full_text") or ""))

    logger.info("👁 Пользователь запросил полный текст отчёта: date=%s type=%s", date_str, report_type)

    return await show_day_detail(update, context, notice="Отчёт отправлен выше.")


async def view_previous_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    date_str = context.user_data.get("report_date")
    report_type = _get_report_type(context)

    if not date_str:
        return await show_reports_menu(update, context)

    prev_report = get_previous_report(date_str, report_type)

    if not prev_report:
        return await show_day_detail(update, context, notice="⚠️ Предыдущий отчёт не найден.")

    chat_id = update.effective_chat.id

    if not chat_id:
        return _state(context, REPORT_VIEW_DETAIL)

    header = (
        f"📄 Предыдущий отчёт\n"
        f"{REPORT_TYPE_LABELS.get(report_type, report_type)}\n"
        f"🗓 {format_date_ru(prev_report.get('date'))}\n\n"
    )

    await send_long_message(context, chat_id, header + (prev_report.get("full_text") or ""))

    logger.info("📄 Пользователь запросил предыдущий отчёт: type=%s", report_type)

    return await show_day_detail(update, context, notice="Предыдущий отчёт отправлен выше.")


# =========================================================
# MAIN CALLBACK ROUTER
# =========================================================

async def report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    if not query:
        return _current_state(context)

    data = query.data or ""
    state = _current_state(context)

    if data == CB_NOOP:
        await _answer(query)
        return state

    # Защита во время ввода текста
    if state == REPORT_AWAIT_TEXT:
        if data == CB_REPORT_TEMPLATE:
            await _answer(query)
            return await send_report_template(update, context)

        if data == CB_REPORT_CANCEL:
            await _answer(query)
            return await cancel_report_creation(update, context)

        if data == CB_REPORT_BACK_MENU:
            await _answer(query)
            _clear_draft(context)
            return await _go_main_menu(update, context, query.message.message_id if query.message else None)

        await _answer(query, "Сначала отправьте текст отчёта или нажмите «Отмена».", True)
        return state

    # Защита во время подтверждения
    if state == REPORT_CONFIRM_SAVE:
        if data == CB_REPORT_SAVE:
            await _answer(query)
            return await save_report_action(update, context)

        if data == CB_REPORT_REENTER:
            await _answer(query)
            return await reenter_report_text(update, context)

        if data == CB_REPORT_CANCEL:
            await _answer(query)
            return await cancel_report_creation(update, context)

        if data == CB_REPORT_BACK_MENU:
            await _answer(query)
            _clear_draft(context)
            return await _go_main_menu(update, context, query.message.message_id if query.message else None)

        await _answer(query, "Сначала сохраните, измените или отмените отчёт.", True)
        return state

    await _answer(query)

    # Главное меню
    if data == CB_REPORT_BACK_MENU:
        _clear_draft(context)
        return await _go_main_menu(update, context, query.message.message_id if query.message else None)

    # Назад к календарю
    if data == CB_REPORT_TO_CALENDAR:
        return await show_reports_menu(update, context)

    # Переключение типа отчёта
    if data.startswith(CB_REPORT_TYPE_PREFIX):
        report_type = data.split(":", 1)[1]

        if report_type in REPORT_TYPE_LABELS:
            context.user_data["report_type"] = report_type

            logger.info("🔀 Переключён тип отчёта: %s", report_type)

        return await show_reports_menu(update, context)

    # Навигация по месяцам
    if data in (CB_REPORT_PREV_MONTH, CB_REPORT_NEXT_MONTH):
        now = now_msk()

        year = context.user_data.get("calendar_year", now.year)
        month = context.user_data.get("calendar_month", now.month)

        if data == CB_REPORT_PREV_MONTH:
            if month == 1:
                month = 12
                year -= 1
            else:
                month -= 1
        else:
            if month == 12:
                month = 1
                year += 1
            else:
                month += 1

        context.user_data["calendar_year"] = year
        context.user_data["calendar_month"] = month

        logger.info("📅 Открыт месяц: %s %s", MONTHS[month - 1], year)

        return await show_reports_menu(update, context)

    # Выбор даты
    if data.startswith(CB_REPORT_DATE_PREFIX):
        raw_date = data.split(":", 1)[1]

        try:
            date_str = datetime.strptime(raw_date, "%Y%m%d").strftime("%Y-%m-%d")
        except Exception:
            return await show_reports_menu(update, context, notice="⚠️ Не удалось прочитать дату.")

        context.user_data["report_date"] = date_str

        logger.info("📆 Выбрана дата отчёта: %s", date_str)

        return await show_day_detail(update, context)

    # Создание / редактирование
    if data == CB_REPORT_CREATE:
        return await start_report_creation(update, context, edit=False)

    if data == CB_REPORT_EDIT:
        return await start_report_creation(update, context, edit=True)

    # Просмотр
    if data == CB_REPORT_VIEW:
        return await view_report_full(update, context)

    if data == CB_REPORT_PREV_REPORT:
        return await view_previous_report(update, context)

    # Fallback
    return await show_reports_menu(update, context)