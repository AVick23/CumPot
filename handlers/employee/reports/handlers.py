import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

try:
    from utils.time_utils import now_msk, today_msk_str
except Exception:
    def now_msk():
        return datetime.now()

    def today_msk_str():
        return datetime.now().strftime("%Y-%m-%d")

from .constants import (
    REPORT_HOME,
    REPORT_HISTORY,
    REPORT_EDITOR,
    REPORT_AWAIT_TEXT,
    REPORT_AWAIT_SECTION,
    CB_NOOP,
    CB_REPORT_BACK_MENU,
    CB_REPORT_HOME,
    CB_REPORT_HISTORY,
    CB_REPORT_OPEN_PREFIX,
    CB_REPORT_TYPE_PREFIX,
    CB_REPORT_DATE_PREFIX,
    CB_REPORT_PREV_MONTH,
    CB_REPORT_NEXT_MONTH,
    CB_REPORT_SAVE,
    CB_REPORT_TEXT_MODE,
    CB_REPORT_LOAD_PREV,
    CB_REPORT_CLEAR,
    CB_REPORT_SECTION_PREFIX,
    CB_REPORT_BACK_EDITOR,
    CB_REPORT_CANCEL,
    REPORT_TYPE_LABELS,
    REPORT_SECTIONS,
    MONTHS,
)

from .keyboards import (
    today_dashboard_keyboard,
    history_calendar_keyboard,
    report_editor_keyboard,
    section_prompt_keyboard,
    text_prompt_keyboard,
)

from .utils import (
    render,
    get_report,
    get_dates_with_reports,
    save_report,
    draft_from_report,
    draft_from_last_report,
    empty_draft,
    parse_report_sections,
    build_full_text,
    build_dashboard_text,
    build_editor_text,
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


def _clear_editing(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("report_draft", None)
    context.user_data.pop("awaiting_section", None)


async def _go_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id=None):
    _clear_editing(context)

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

    return MAIN_MENU


# =========================================================
# HOME / TODAY DASHBOARD
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

    today = today_msk_str()

    opening_report = get_report(today, "opening")
    closing_report = get_report(today, "closing")

    text = build_dashboard_text(today, opening_report, closing_report)

    if notice:
        text = f"{notice}\n\n{text}"

    kb = today_dashboard_keyboard(
        opening_exists=bool(opening_report),
        closing_exists=bool(closing_report),
    )

    await render(update, context, text, kb, message_id)

    return _state(context, REPORT_HOME)


# =========================================================
# HISTORY
# =========================================================

async def show_history_calendar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
    notice=None,
) -> int:
    now = now_msk()

    year = context.user_data.get("calendar_year", now.year)
    month = context.user_data.get("calendar_month", now.month)

    if not (1 <= month <= 12):
        month = now.month

    context.user_data["calendar_year"] = year
    context.user_data["calendar_month"] = month

    report_type = _get_report_type(context)

    dates_with_reports = get_dates_with_reports(year, month, report_type)

    today = now.strftime("%Y-%m-%d")

    text = (
        "🗓 История отчётов\n\n"
        f"{REPORT_TYPE_LABELS[report_type]}\n"
        f"{MONTHS[month - 1]} {year}\n\n"
        "📌 — отчёт есть\n"
        "• — сегодня"
    )

    if notice:
        text = f"{notice}\n\n{text}"

    kb = history_calendar_keyboard(
        report_type=report_type,
        year=year,
        month=month,
        dates_with_reports=dates_with_reports,
        today=today,
    )

    await render(update, context, text, kb, message_id)

    return _state(context, REPORT_HISTORY)


# =========================================================
# EDITOR
# =========================================================

async def open_report_editor(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    date_str: str | None = None,
    report_type: str | None = None,
    message_id=None,
    notice=None,
) -> int:
    user = update.effective_user

    if not user:
        return MAIN_MENU

    date_str = date_str or today_msk_str()
    report_type = report_type or _get_report_type(context)

    if report_type not in REPORT_TYPE_LABELS:
        report_type = "opening"

    context.user_data["report_date"] = date_str
    context.user_data["report_type"] = report_type

    existing_report = get_report(date_str, report_type)

    if existing_report:
        draft = draft_from_report(existing_report, report_type, source="saved")
        default_notice = "✅ Открыт сохранённый отчёт."
    else:
        draft = draft_from_last_report(date_str, report_type)

        if draft.get("source") == "prev":
            default_notice = "📋 Создан черновик на основе последнего отчёта."
        else:
            default_notice = "🆕 Создан новый шаблон."

    context.user_data["report_draft"] = draft

    logger.info(
        "📝 Пользователь %s открыл редактор отчёта: date=%s type=%s source=%s",
        user.id,
        date_str,
        report_type,
        draft.get("source"),
    )

    return await render_report_editor(update, context, message_id, notice or default_notice)


async def render_report_editor(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
    notice=None,
) -> int:
    draft = context.user_data.get("report_draft")

    if not draft:
        return await show_reports_menu(update, context, message_id)

    date_str = context.user_data.get("report_date") or today_msk_str()
    report_type = _get_report_type(context)

    text = build_editor_text(draft, date_str, report_type)

    if notice:
        text = f"{notice}\n\n{text}"

    kb = report_editor_keyboard(draft)

    await render(update, context, text, kb, message_id)

    return _state(context, REPORT_EDITOR)


async def edit_section(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    section_index: int,
    message_id=None,
) -> int:
    draft = context.user_data.get("report_draft")

    if not draft:
        return await show_reports_menu(update, context, message_id)

    order = draft.get("order", [])

    if section_index < 0 or section_index >= len(order):
        return await render_report_editor(update, context, message_id)

    section = order[section_index]
    value = draft.get("values", {}).get(section, "")

    context.user_data["awaiting_section"] = section

    text = (
        f"✏️ {section}\n\n"
        f"Текущее значение:\n{value or '—'}\n\n"
        "Отправьте новое значение.\n"
        "Можно несколько строк."
    )

    kb = section_prompt_keyboard()

    await render(update, context, text, kb, message_id)

    logger.info("✏️ Пользователь редактирует раздел: %s", section)

    return _state(context, REPORT_AWAIT_SECTION)


async def save_report_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user

    if not user:
        return MAIN_MENU

    draft = context.user_data.get("report_draft")
    date_str = context.user_data.get("report_date")
    report_type = _get_report_type(context)

    if not draft or not date_str:
        return await show_reports_menu(update, context, notice="⚠️ Данные утеряны. Начните заново.")

    values = draft.get("values", {})
    raw = draft.get("raw")

    has_values = any((value or "").strip() for value in values.values())

    if raw and not has_values:
        full_text = raw
        parsed = {}
    else:
        full_text = build_full_text(report_type, values)
        parsed = {
            key: value
            for key, value in values.items()
            if (value or "").strip()
        }

    save_report(date_str, report_type, user.id, full_text, parsed)

    _clear_editing(context)

    logger.info(
        "✅ Пользователь %s сохранил отчёт: date=%s type=%s",
        user.id,
        date_str,
        report_type,
    )

    return await show_reports_menu(update, context, notice="✅ Отчёт сохранён.")


async def load_previous_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    date_str = context.user_data.get("report_date") or today_msk_str()
    report_type = _get_report_type(context)

    draft = draft_from_last_report(date_str, report_type)

    context.user_data["report_draft"] = draft

    logger.info("📋 Загружен последний отчёт как черновик: type=%s", report_type)

    if draft.get("source") == "prev":
        notice = "📋 Загружен последний отчёт."
    else:
        notice = "⚠️ Предыдущих отчётов нет."

    return await render_report_editor(update, context, notice=notice)


async def clear_draft(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    report_type = _get_report_type(context)

    draft = empty_draft(report_type)
    draft["source"] = "empty"

    context.user_data["report_draft"] = draft

    logger.info("🗑 Черновик очищен")

    return await render_report_editor(update, context, notice="🗑 Черновик очищен.")


async def show_text_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    date_str = context.user_data.get("report_date") or today_msk_str()
    report_type = _get_report_type(context)

    text = (
        "🧾 Отправка текстом\n\n"
        f"{REPORT_TYPE_LABELS[report_type]} · {date_str}\n\n"
        "Отправьте отчёт одним сообщением.\n"
        "Я распознаю разделы и покажу черновик."
    )

    kb = text_prompt_keyboard()

    await render(update, context, text, kb)

    logger.info("🧾 Пользователь перешёл в режим отправки текста")

    return _state(context, REPORT_AWAIT_TEXT)


# =========================================================
# TEXT INPUT
# =========================================================

async def receive_report_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user

    if not user:
        return MAIN_MENU

    state = _current_state(context)

    text = (update.message.text or "").strip() if update.message else ""

    if not text:
        await update.message.reply_text("⚠️ Пустой текст. Попробуйте ещё раз.")
        return state

    # Редактирование одного раздела
    if state == REPORT_AWAIT_SECTION:
        section = context.user_data.get("awaiting_section")
        draft = context.user_data.get("report_draft")

        if not section or not draft:
            return await show_reports_menu(update, context)

        draft.setdefault("values", {})[section] = text
        draft["raw"] = None

        context.user_data.pop("awaiting_section", None)
        context.user_data["report_draft"] = draft

        logger.info("✅ Раздел обновлён: %s", section)

        return await render_report_editor(update, context, notice="✅ Раздел обновлён.")

    # Полный текст
    draft = context.user_data.get("report_draft")

    if not draft:
        report_type = _get_report_type(context)
        date_str = context.user_data.get("report_date") or today_msk_str()

        context.user_data["report_date"] = date_str
        context.user_data["report_type"] = report_type

        draft = empty_draft(report_type)

    report_type = draft.get("type") or _get_report_type(context)

    parsed = parse_report_sections(text, report_type)

    if parsed:
        for section in draft.get("order", []):
            draft.setdefault("values", {})[section] = parsed.get(section, "") or ""

        draft["raw"] = None
        draft["source"] = "text"

        notice = "✅ Текст распознан. Проверьте черновик."
    else:
        draft["raw"] = text
        draft["source"] = "text"

        notice = "⚠️ Разделы не распознаны. Можно сохранить как есть."

    context.user_data["report_draft"] = draft

    logger.info("🧾 Получен текст отчёта, распознано разделов: %s", len(parsed))

    return await render_report_editor(update, context, notice=notice)


# =========================================================
# MAIN CALLBACK ROUTER
# =========================================================

async def report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    if not query:
        return _current_state(context)

    data = query.data or ""
    state = _current_state(context)
    message_id = query.message.message_id if query.message else None

    if data == CB_NOOP:
        await _answer(query)
        return state

    # ----------------------------------------------------
    # GUARD: ожидание значения раздела
    # ----------------------------------------------------
    if state == REPORT_AWAIT_SECTION:
        if data == CB_REPORT_BACK_EDITOR:
            await _answer(query)
            context.user_data.pop("awaiting_section", None)
            return await render_report_editor(update, context, message_id)

        if data == CB_REPORT_CANCEL:
            await _answer(query)
            _clear_editing(context)
            return await show_reports_menu(update, context, message_id, notice="Отменено.")

        if data == CB_REPORT_BACK_MENU:
            await _answer(query)
            return await _go_main_menu(update, context, message_id)

        await _answer(query, "Сначала отправьте новое значение раздела.", True)
        return state

    # ----------------------------------------------------
    # GUARD: ожидание полного текста
    # ----------------------------------------------------
    if state == REPORT_AWAIT_TEXT:
        if data == CB_REPORT_BACK_EDITOR:
            await _answer(query)
            return await render_report_editor(update, context, message_id)

        if data == CB_REPORT_CANCEL:
            await _answer(query)
            _clear_editing(context)
            return await show_reports_menu(update, context, message_id, notice="Отменено.")

        if data == CB_REPORT_BACK_MENU:
            await _answer(query)
            return await _go_main_menu(update, context, message_id)

        await _answer(query, "Сначала отправьте текст отчёта.", True)
        return state

    await _answer(query)

    # ----------------------------------------------------
    # GENERAL NAVIGATION
    # ----------------------------------------------------

    if data == CB_REPORT_BACK_MENU:
        return await _go_main_menu(update, context, message_id)

    if data == CB_REPORT_HOME:
        _clear_editing(context)
        return await show_reports_menu(update, context, message_id)

    # ----------------------------------------------------
    # HOME SCREEN
    # ----------------------------------------------------
    if state == REPORT_HOME:
        if data.startswith(CB_REPORT_OPEN_PREFIX):
            report_type = data.split(":", 1)[1]
            today = today_msk_str()

            return await open_report_editor(
                update,
                context,
                date_str=today,
                report_type=report_type,
                message_id=message_id,
            )

        if data == CB_REPORT_HISTORY:
            return await show_history_calendar(update, context, message_id)

        return await show_reports_menu(update, context, message_id)

    # ----------------------------------------------------
    # HISTORY SCREEN
    # ----------------------------------------------------
    if state == REPORT_HISTORY:
        if data.startswith(CB_REPORT_TYPE_PREFIX):
            report_type = data.split(":", 1)[1]

            if report_type in REPORT_TYPE_LABELS:
                context.user_data["report_type"] = report_type

            return await show_history_calendar(update, context, message_id)

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

            return await show_history_calendar(update, context, message_id)

        if data.startswith(CB_REPORT_DATE_PREFIX):
            raw_date = data.split(":", 1)[1]

            try:
                date_str = datetime.strptime(raw_date, "%Y%m%d").strftime("%Y-%m-%d")
            except Exception:
                return await show_history_calendar(update, context, message_id)

            report_type = _get_report_type(context)

            return await open_report_editor(
                update,
                context,
                date_str=date_str,
                report_type=report_type,
                message_id=message_id,
            )

        return await show_history_calendar(update, context, message_id)

    # ----------------------------------------------------
    # EDITOR SCREEN
    # ----------------------------------------------------
    if state == REPORT_EDITOR:
        if data == CB_REPORT_SAVE:
            return await save_report_action(update, context)

        if data == CB_REPORT_TEXT_MODE:
            return await show_text_mode(update, context)

        if data == CB_REPORT_LOAD_PREV:
            return await load_previous_report(update, context)

        if data == CB_REPORT_CLEAR:
            return await clear_draft(update, context)

        if data.startswith(CB_REPORT_SECTION_PREFIX):
            try:
                section_index = int(data.split(":", 1)[1])
            except Exception:
                return await render_report_editor(update, context, message_id)

            return await edit_section(update, context, section_index, message_id)

        if data == CB_REPORT_CANCEL:
            _clear_editing(context)
            return await show_reports_menu(update, context, message_id, notice="Отменено.")

        if data == CB_REPORT_HOME:
            _clear_editing(context)
            return await show_reports_menu(update, context, message_id)

        return await render_report_editor(update, context, message_id)

    # Fallback
    return await show_reports_menu(update, context, message_id)