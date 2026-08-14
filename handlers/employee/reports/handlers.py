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
    REPORT_EDITOR,
    REPORT_TEXT_MODE,
    REPORT_SECTION_MENU,
    REPORT_SECTION_LIST,
    REPORT_AWAIT_SECTION,
    CB_NOOP,
    CB_REPORT_BACK_MENU,
    CB_REPORT_OPEN_PREFIX,
    CB_REPORT_SAVE,
    CB_REPORT_TEXT_MODE,
    CB_REPORT_LOAD_LAST,
    CB_REPORT_CLEAR,
    CB_REPORT_SECTION_MODE,
    CB_REPORT_CANCEL,
    CB_REPORT_BACK_EDITOR,
    CB_REPORT_SECTION_MENU_CLEAR,
    CB_REPORT_SECTION_START,
    CB_REPORT_SECTION_CHOOSE,
    CB_REPORT_SECTION_PREFIX,
    CB_REPORT_SECTION_DONE,
    CB_REPORT_SECTION_SKIP,
    CB_REPORT_SECTION_EXIT,
    REPORT_TYPE_LABELS,
    REPORT_SECTIONS,
    EDITOR_INLINE_LIMIT,
)

from .keyboards import (
    report_home_keyboard,
    report_editor_keyboard,
    section_mode_keyboard,
    section_list_keyboard,
    section_prompt_keyboard,
    text_prompt_keyboard,
)

from .utils import (
    render,
    send_long_message,
    get_report,
    save_report,
    load_draft,
    draft_from_last,
    empty_draft,
    draft_full_text,
    parse_report_sections,
    format_date_ru,
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


def _get_draft(context: ContextTypes.DEFAULT_TYPE) -> dict | None:
    return context.user_data.get("report_draft")


def _set_draft(context: ContextTypes.DEFAULT_TYPE, draft: dict | None) -> None:
    if draft is None:
        context.user_data.pop("report_draft", None)
    else:
        context.user_data["report_draft"] = draft


def _clear_guided(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("guided", None)
    context.user_data.pop("guided_index", None)
    context.user_data.pop("awaiting_section", None)


async def _go_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id=None):
    _set_draft(context, None)
    _clear_guided(context)

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


def _source_label(draft: dict) -> str:
    source = draft.get("source", "empty")
    source_date = draft.get("source_date")

    if source == "saved":
        return "✅ Сохранённый отчёт"

    if source == "prev" and source_date:
        return f"📋 Черновик на основе отчёта за {format_date_ru(source_date)}"

    if source == "text":
        return "🧾 Текст обновлён"

    return "🆕 Новый черновик"


# =========================================================
# HOME SCREEN
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

    lines = [
        "📋 Отчёты",
        "",
        f"Сегодня, {format_date_ru(today)}",
        "",
    ]

    for report_type, report in [
        ("opening", opening_report),
        ("closing", closing_report),
    ]:
        label = REPORT_TYPE_LABELS.get(report_type, report_type)

        if report:
            lines.append(f"{label}: ✅ сохранён")
        else:
            lines.append(f"{label}: ⚪️ не заполнен")

    lines.append("")
    lines.append("Нажмите, чтобы открыть или заполнить.")

    text = "\n".join(lines)

    if notice:
        text = f"{notice}\n\n{text}"

    kb = report_home_keyboard(
        opening_exists=bool(opening_report),
        closing_exists=bool(closing_report),
    )

    await render(update, context, text, kb, message_id)

    return _state(context, REPORT_HOME)


# =========================================================
# EDITOR SCREEN
# =========================================================

async def open_report_editor(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    report_type: str,
    message_id=None,
) -> int:
    user = update.effective_user

    if not user:
        return MAIN_MENU

    date_str = today_msk_str()

    context.user_data["report_date"] = date_str
    context.user_data["report_type"] = report_type

    draft = load_draft(date_str, report_type)
    _set_draft(context, draft)

    logger.info(
        "📝 Пользователь %s открыл редактор отчёта: date=%s type=%s source=%s",
        user.id,
        date_str,
        report_type,
        draft.get("source"),
    )

    return await show_editor(update, context, message_id, send_full=True)


async def show_editor(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
    notice=None,
    send_full: bool = False,
) -> int:
    draft = _get_draft(context)

    if not draft:
        return await show_reports_menu(update, context, message_id)

    date_str = draft.get("date")
    report_type = draft.get("type")

    full_text = draft_full_text(draft)

    type_label = REPORT_TYPE_LABELS.get(report_type, report_type)

    header_lines = [
        type_label,
        f"🗓 {format_date_ru(date_str)}",
        _source_label(draft),
    ]

    if notice:
        header_lines.insert(0, notice)

    header = "\n".join(header_lines)

    chat_id = update.effective_chat.id

    if len(full_text) <= EDITOR_INLINE_LIMIT:
        text = f"{header}\n\n{full_text}"

        await render(
            update,
            context,
            text,
            report_editor_keyboard(),
            message_id,
        )
    else:
        if send_full and chat_id:
            await send_long_message(context, chat_id, full_text)

        panel_text = f"{header}\n\n📄 Полный текст отправлен выше."

        await render(
            update,
            context,
            panel_text,
            report_editor_keyboard(),
            message_id,
        )

    return _state(context, REPORT_EDITOR)


# =========================================================
# EDITOR ACTIONS
# =========================================================

async def save_report_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user

    if not user:
        return MAIN_MENU

    draft = _get_draft(context)

    if not draft:
        return await show_reports_menu(update, context)

    date_str = draft.get("date")
    report_type = draft.get("type")

    full_text = draft_full_text(draft)

    if not full_text.strip():
        return await show_editor(
            update,
            context,
            notice="⚠️ Отчёт пуст.",
            send_full=False,
        )

    parsed = parse_report_sections(full_text, report_type)

    save_report(
        date_str=date_str,
        report_type=report_type,
        author_id=user.id,
        full_text=full_text,
        parsed=parsed,
    )

    logger.info(
        "✅ Пользователь %s сохранил отчёт: date=%s type=%s",
        user.id,
        date_str,
        report_type,
    )

    _set_draft(context, None)
    _clear_guided(context)

    return await show_reports_menu(update, context, notice="✅ Отчёт сохранён.")


async def show_text_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    draft = _get_draft(context)

    if not draft:
        return await show_reports_menu(update, context)

    date_str = draft.get("date")
    report_type = draft.get("type")

    text = (
        "🧾 Отправка текстом\n\n"
        f"{REPORT_TYPE_LABELS.get(report_type)} · {format_date_ru(date_str)}\n\n"
        "Отправьте отчёт одним сообщением.\n"
        "Я распознаю разделы, если они есть."
    )

    await render(update, context, text, text_prompt_keyboard())

    logger.info("🧾 Пользователь перешёл в текстовый режим отчёта")

    return _state(context, REPORT_TEXT_MODE)


async def load_last_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    draft = _get_draft(context)

    if not draft:
        return await show_reports_menu(update, context)

    date_str = draft.get("date")
    report_type = draft.get("type")

    new_draft = draft_from_last(date_str, report_type)

    if new_draft.get("source") == "prev":
        notice = "📋 Загружен последний отчёт."
    else:
        notice = "⚠️ Предыдущих отчётов нет."

    _set_draft(context, new_draft)

    logger.info("📋 Загружен последний отчёт как черновик: type=%s", report_type)

    return await show_editor(update, context, notice=notice, send_full=True)


async def clear_report_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    draft = _get_draft(context)

    if not draft:
        return await show_reports_menu(update, context)

    date_str = draft.get("date")
    report_type = draft.get("type")

    new_draft = empty_draft(date_str, report_type)

    _set_draft(context, new_draft)

    logger.info("🗑 Отчёт очищен")

    return await show_editor(
        update,
        context,
        notice="🗑 Отчёт очищен.",
        send_full=True,
    )


# =========================================================
# SECTION MODE
# =========================================================

async def show_section_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    draft = _get_draft(context)

    if not draft:
        return await show_reports_menu(update, context)

    text = (
        "🧩 По пунктам\n\n"
        "Выберите действие:\n"
        "• очистить весь отчёт\n"
        "• заполнить с нуля по шагам\n"
        "• выбрать пункт вручную"
    )

    await render(update, context, text, section_mode_keyboard())

    logger.info("🧩 Открыто меню работы по пунктам")

    return _state(context, REPORT_SECTION_MENU)


async def show_section_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
    notice=None,
) -> int:
    draft = _get_draft(context)

    if not draft:
        return await show_reports_menu(update, context)

    report_type = draft.get("type")
    values = draft.get("values", {})
    sections = REPORT_SECTIONS.get(report_type, [])

    filled = sum(
        1
        for section in sections
        if (values.get(section) or "").strip()
    )

    text = (
        "🧩 Пункты отчёта\n\n"
        f"Заполнено: {filled}/{len(sections)}\n\n"
        "Нажмите на пункт, чтобы изменить его."
    )

    if notice:
        text = f"{notice}\n\n{text}"

    kb = section_list_keyboard(values, sections)

    await render(update, context, text, kb, message_id)

    return _state(context, REPORT_SECTION_LIST)


async def prompt_section(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    section_index: int,
    guided: bool,
) -> int:
    draft = _get_draft(context)

    if not draft:
        return await show_reports_menu(update, context)

    report_type = draft.get("type")
    sections = REPORT_SECTIONS.get(report_type, [])

    if section_index < 0 or section_index >= len(sections):
        return await show_editor(update, context)

    section = sections[section_index]
    value = draft.get("values", {}).get(section, "")

    context.user_data["awaiting_section"] = section
    context.user_data["guided"] = guided
    context.user_data["guided_index"] = section_index

    if guided:
        header = f"🚀 Шаг {section_index + 1}/{len(sections)}"
    else:
        header = "✏️ Редактирование пункта"

    text = (
        f"{header}\n\n"
        f"📌 {section}\n\n"
        f"Текущее значение:\n{value or '—'}\n\n"
        "Отправьте новое значение.\n"
        "Можно несколько строк."
    )

    kb = section_prompt_keyboard(guided)

    await render(update, context, text, kb)

    logger.info("✏️ Редактируется раздел: %s", section)

    return _state(context, REPORT_AWAIT_SECTION)


async def _advance_guided_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    draft = _get_draft(context)

    if not draft:
        return await show_reports_menu(update, context)

    report_type = draft.get("type")
    sections = REPORT_SECTIONS.get(report_type, [])

    index = context.user_data.get("guided_index", 0)
    index += 1

    if index < len(sections):
        return await prompt_section(update, context, index, guided=True)

    _clear_guided(context)

    return await show_editor(
        update,
        context,
        notice="✅ Все пункты заполнены.",
        send_full=True,
    )


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

    draft = _get_draft(context)

    # Пользователь просто прислал текст в редакторе — считаем, что это новый полный текст.
    if state == REPORT_EDITOR:
        if not draft:
            return await show_reports_menu(update, context)

        report_type = draft.get("type", "opening")

        draft["raw"] = text
        draft["values"] = parse_report_sections(text, report_type)
        draft["source"] = "text"

        _set_draft(context, draft)

        logger.info("🧾 Пользователь прислал полный текст отчёта в редакторе")

        return await show_editor(
            update,
            context,
            notice="✅ Текст обновлён.",
            send_full=True,
        )

    # Текстовый режим
    if state == REPORT_TEXT_MODE:
        if not draft:
            return await show_reports_menu(update, context)

        report_type = draft.get("type", "opening")

        draft["raw"] = text
        draft["values"] = parse_report_sections(text, report_type)
        draft["source"] = "text"

        _set_draft(context, draft)

        logger.info("🧾 Получен текст отчёта в текстовом режиме")

        return await show_editor(
            update,
            context,
            notice="✅ Текст обновлён.",
            send_full=True,
        )

    # Ввод значения конкретного пункта
    if state == REPORT_AWAIT_SECTION:
        if not draft:
            return await show_reports_menu(update, context)

        section = context.user_data.get("awaiting_section")

        if not section:
            return await show_editor(update, context)

        draft.setdefault("values", {})[section] = text
        draft["raw"] = None
        draft["source"] = "sections"

        _set_draft(context, draft)

        guided = bool(context.user_data.get("guided"))

        logger.info("✅ Раздел обновлён: %s", section)

        if guided:
            return await _advance_guided_flow(update, context)

        return await show_section_list(
            update,
            context,
            notice="✅ Пункт обновлён.",
        )

    return state


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
        if data == CB_REPORT_SECTION_SKIP:
            await _answer(query)
            
            draft = _get_draft(context)
            section = context.user_data.get("awaiting_section")
            
            if draft and section:
                draft.setdefault("values", {})[section] = ""
                draft["raw"] = None
                draft["source"] = "sections"
                _set_draft(context, draft)
                
            guided = bool(context.user_data.get("guided"))
            if guided:
                return await _advance_guided_flow(update, context)
            return await show_section_list(update, context, notice="🗑 Пункт очищен.")

        if data in (CB_REPORT_SECTION_EXIT, CB_REPORT_BACK_EDITOR, CB_REPORT_CANCEL):
            await _answer(query)
            _clear_guided(context)
            return await show_editor(update, context, message_id)

        await _answer(query, "Сначала отправьте новое значение раздела.", True)
        return state

    # ----------------------------------------------------
    # GUARD: ожидание полного текста
    # ----------------------------------------------------
    if state == REPORT_TEXT_MODE:
        if data in (CB_REPORT_BACK_EDITOR, CB_REPORT_CANCEL):
            await _answer(query)
            return await show_editor(update, context, message_id)

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

    # ----------------------------------------------------
    # HOME SCREEN
    # ----------------------------------------------------
    if state == REPORT_HOME:
        if data.startswith(CB_REPORT_OPEN_PREFIX):
            report_type = data.split(":", 1)[1]
            return await open_report_editor(
                update,
                context,
                report_type=report_type,
                message_id=message_id,
            )

        return await show_reports_menu(update, context, message_id)

    # ----------------------------------------------------
    # EDITOR SCREEN
    # ----------------------------------------------------
    if state == REPORT_EDITOR:
        if data == CB_REPORT_SAVE:
            return await save_report_action(update, context)

        if data == CB_REPORT_TEXT_MODE:
            return await show_text_mode(update, context)

        if data == CB_REPORT_LOAD_LAST:
            return await load_last_action(update, context)

        if data == CB_REPORT_CLEAR:
            return await clear_report_action(update, context)

        if data == CB_REPORT_SECTION_MODE:
            return await show_section_menu(update, context)

        if data == CB_REPORT_CANCEL:
            _set_draft(context, None)
            _clear_guided(context)
            return await show_reports_menu(update, context, message_id, notice="Отменено.")

        return await show_editor(update, context, message_id)

    # ----------------------------------------------------
    # SECTION MENU
    # ----------------------------------------------------
    if state == REPORT_SECTION_MENU:
        if data == CB_REPORT_SECTION_MENU_CLEAR:
            return await clear_report_action(update, context)

        if data == CB_REPORT_SECTION_START:
            draft = _get_draft(context)
            if not draft:
                return await show_reports_menu(update, context)
            
            new_draft = empty_draft(draft.get("date"), draft.get("type"))
            _set_draft(context, new_draft)
            
            return await prompt_section(update, context, 0, guided=True)

        if data == CB_REPORT_SECTION_CHOOSE:
            return await show_section_list(update, context, message_id)

        if data == CB_REPORT_BACK_EDITOR:
            return await show_editor(update, context, message_id)

        return await show_section_menu(update, context)

    # ----------------------------------------------------
    # SECTION LIST
    # ----------------------------------------------------
    if state == REPORT_SECTION_LIST:
        if data.startswith(CB_REPORT_SECTION_PREFIX):
            try:
                section_index = int(data.split(":", 1)[1])
            except (TypeError, ValueError):
                return await show_section_list(update, context, message_id)

            return await prompt_section(update, context, section_index, guided=False)

        if data in (CB_REPORT_SECTION_DONE, CB_REPORT_BACK_EDITOR):
            return await show_editor(update, context, message_id, send_full=True)

        return await show_section_list(update, context, message_id)

    # Fallback
    return await show_reports_menu(update, context, message_id)