import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from db.users import get_user, update_user_profile

from .constants import (
    ONBOARD_NAME,
    ONBOARD_POSITION,
    MAIN_MENU,
    CATEGORY_SELECT,
    CHECKLIST_VIEW,
    ITEM_DETAIL,
    PROGRESS_VIEW,
    END_SHIFT_CONFIRM,
    CB_NOOP,
    CB_START_SHIFT,
    CB_END_SHIFT,
    CB_END_SHIFT_CONFIRM,
    CB_END_SHIFT_CANCEL,
    CB_CHECKLIST,
    CB_PROGRESS,
    CB_POSITION_PREFIX,
    CB_CATEGORY_PREFIX,
    CB_ITEM_PREFIX,
    CB_TOGGLE_PREFIX,
    CB_BACK_MENU,
    CB_BACK_CATEGORIES,
    LOCATIONS,
    CATEGORY_NAMES,
    MSG_LIMIT,
    FULL_NAME_LIMIT,
)

from .keyboards import (
    position_keyboard,
    main_menu_keyboard,
    back_menu_keyboard,
    categories_keyboard,
    checklist_keyboard,
    item_detail_keyboard,
    progress_keyboard,
    end_shift_keyboard,
)

from .utils import (
    get_position_label,
    start_shift_for_user,
    get_current_shift,
    end_current_shift,
    get_categories_stats,
    get_items_by_category,
    get_item_by_id,
    toggle_item,
    get_user_progress_summary,
    progress_bar,
    percent,
)

logger = logging.getLogger(__name__)


def set_state(context: ContextTypes.DEFAULT_TYPE, state: int) -> int:
    context.user_data["employee_state"] = state
    return state


def current_state(context: ContextTypes.DEFAULT_TYPE) -> int:
    return context.user_data.get("employee_state", MAIN_MENU)


def truncate_text(text: str | None, limit: int = MSG_LIMIT) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + "…"


async def answer(query, text: str | None = None) -> None:
    try:
        await query.answer(text or "")
    except Exception:
        pass


async def render(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup=None,
    message_id: int | None = None,
) -> int | None:
    text = truncate_text(text, MSG_LIMIT)
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
        except BadRequest as e:
            if "Message is not modified" in str(e):
                return message_id
            logger.warning("Employee edit failed: %s", e)

    if chat_id:
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
        )
        return msg.message_id

    return None


# =========================
# ONBOARDING
# =========================

async def ask_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
    error: str | None = None,
) -> int:
    text = (
        "👋 Добро пожаловать!\n\n"
        "Чтобы продолжить, укажите ваше ФИО полностью.\n\n"
        "Например:\n"
        "Иванов Иван Иванович"
    )

    if error:
        text = f"⚠️ {error}\n\n{text}"

    new_message_id = await render(update, context, text, None, message_id)
    context.user_data["onboarding_msg_id"] = new_message_id

    return set_state(context, ONBOARD_NAME)


async def ask_position(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
    error: str | None = None,
) -> int:
    text = "Отлично! Теперь выберите, где вы работаете."

    if error:
        text = f"⚠️ {error}\n\n{text}"

    new_message_id = await render(update, context, text, position_keyboard(), message_id)
    context.user_data["onboarding_msg_id"] = new_message_id

    return set_state(context, ONBOARD_POSITION)


async def employee_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Точка входа для сотрудника.
    Если ФИО и позиция не заполнены — начинаем онбординг.
    """
    user = update.effective_user
    if not user:
        return MAIN_MENU

    user_db = get_user(user.id)

    context.user_data.pop("onboarding_full_name", None)
    context.user_data.pop("onboarding_msg_id", None)
    context.user_data.pop("current_category", None)

    if not user_db or not (user_db.get("full_name") or "").strip():
        return await ask_name(update, context)

    if not (user_db.get("position") or "").strip():
        context.user_data["onboarding_full_name"] = user_db.get("full_name")
        return await ask_position(update, context)

    return await show_main_menu(update, context)


async def onboarding_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return set_state(context, ONBOARD_NAME)

    message_id = context.user_data.get("onboarding_msg_id")

    raw_text = (update.message.text or "").strip()
    full_name = " ".join(raw_text.split())

    if len(full_name) < 5 or len(full_name.split()) < 2:
        return await ask_name(
            update,
            context,
            message_id,
            error="Пожалуйста, укажите ФИО полностью: минимум фамилия и имя."
        )

    if len(full_name) > FULL_NAME_LIMIT:
        return await ask_name(
            update,
            context,
            message_id,
            error=f"Слишком длинно. Максимум {FULL_NAME_LIMIT} символов."
        )

    context.user_data["onboarding_full_name"] = full_name
    return await ask_position(update, context, message_id)


async def onboarding_position(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data or ""

    await answer(query)

    message_id = query.message.message_id if query.message else context.user_data.get("onboarding_msg_id")

    if not data.startswith(CB_POSITION_PREFIX):
        return await ask_position(update, context, message_id, error="Выберите одну из позиций.")

    position = data.split(":", 1)[1]

    if position not in LOCATIONS:
        return await ask_position(update, context, message_id, error="Выберите одну из позиций.")

    user = update.effective_user
    if not user:
        return MAIN_MENU

    user_db = get_user(user.id)
    full_name = context.user_data.get("onboarding_full_name") or (user_db.get("full_name") if user_db else None)

    if not full_name:
        return await ask_name(update, context, message_id, error="Сначала укажите ФИО.")

    update_user_profile(user.id, full_name=full_name, position=position)

    context.user_data.pop("onboarding_full_name", None)
    context.user_data.pop("onboarding_msg_id", None)
    context.user_data.pop("current_category", None)

    return await show_main_menu(
        update,
        context,
        message_id,
        notice="✅ Профиль сохранён. Теперь можно начинать смену."
    )


# =========================
# MAIN MENU
# =========================

async def show_main_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
    notice: str | None = None,
) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU

    user_db = get_user(user.id)

    if not user_db or not (user_db.get("full_name") or "").strip():
        return await ask_name(update, context, message_id)

    if not (user_db.get("position") or "").strip():
        context.user_data["onboarding_full_name"] = user_db.get("full_name")
        return await ask_position(update, context, message_id)

    context.user_data.pop("current_category", None)

    shift = get_current_shift(user.id)
    full_name = user_db.get("full_name") or "Сотрудник"

    if shift:
        shift_location_label = get_position_label(shift.get("location"))
        text = (
            "🟢 Смена открыта\n"
            f"📍 {shift_location_label} · с {shift.get('start_time', '—')}\n\n"
            "Выберите действие."
        )
        kb = main_menu_keyboard(has_shift=True)
    else:
        position_label = get_position_label(user_db.get("position"))
        text = (
            f"👋 {full_name}\n"
            f"Ваша позиция: {position_label}\n\n"
            "Сейчас вы не на смене.\n"
            "Когда будете готовы, начните смену."
        )
        kb = main_menu_keyboard(has_shift=False)

    if notice:
        text = f"{notice}\n\n{text}"

    await render(update, context, text, kb, message_id)
    return set_state(context, MAIN_MENU)


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data or ""

    await answer(query)

    user = update.effective_user
    if not user:
        return MAIN_MENU

    message_id = query.message.message_id if query.message else None

    if data == CB_START_SHIFT:
        active_shift = get_current_shift(user.id)

        if active_shift:
            return await show_main_menu(update, context, message_id, notice="Вы уже на смене.")

        user_db = get_user(user.id)
        if not user_db or not user_db.get("position"):
            return await employee_start(update, context)

        started = start_shift_for_user(user.id)

        if not started:
            return await show_main_menu(update, context, message_id, notice="⚠️ Не удалось начать смену.")

        return await show_main_menu(update, context, message_id, notice="✅ Смена открыта. Хорошей смены!")

    if data == CB_END_SHIFT:
        return await show_end_confirm(update, context, message_id)

    if data == CB_CHECKLIST:
        return await show_categories(update, context, message_id)

    if data == CB_PROGRESS:
        return await show_progress(update, context, message_id)

    if data == CB_BACK_MENU:
        return await show_main_menu(update, context, message_id)

    return await show_main_menu(update, context, message_id)


# =========================
# CHECKLIST CATEGORIES
# =========================

async def show_categories(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
    notice: str | None = None,
) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU

    shift = get_current_shift(user.id)
    if not shift:
        return await show_main_menu(update, context, message_id, notice="Сначала начните смену.")

    stats = get_categories_stats(user.id)

    if stats is None:
        return await show_main_menu(update, context, message_id, notice="Сначала начните смену.")

    if not stats:
        text = "📋 Чек-лист\n\nНа сегодня задач нет."
        if notice:
            text = f"{notice}\n\n{text}"

        await render(update, context, text, back_menu_keyboard(), message_id)
        return set_state(context, CATEGORY_SELECT)

    text = "📋 Чек-лист\n\nВыберите категорию."

    if notice:
        text = f"{notice}\n\n{text}"

    kb = categories_keyboard(stats)
    await render(update, context, text, kb, message_id)

    return set_state(context, CATEGORY_SELECT)


async def category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data or ""

    await answer(query)

    message_id = query.message.message_id if query.message else None

    if data.startswith(CB_CATEGORY_PREFIX):
        category = data.split(":", 1)[1]
        context.user_data["current_category"] = category
        return await show_checklist(update, context, category, message_id)

    if data == CB_BACK_MENU:
        return await show_main_menu(update, context, message_id)

    return await show_categories(update, context, message_id)


# =========================
# CHECKLIST LIST
# =========================

async def show_checklist(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    category: str,
    message_id: int | None = None,
    notice: str | None = None,
) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU

    items = get_items_by_category(user.id, category)

    if items is None:
        return await show_main_menu(update, context, message_id, notice="Сначала начните смену.")

    if not items:
        return await show_categories(update, context, message_id, notice="В этой категории нет задач.")

    context.user_data["current_category"] = category

    done = sum(1 for item in items if item.get("completed"))
    total = len(items)
    bar = progress_bar(done, total)

    category_label = CATEGORY_NAMES.get(category, category)

    text = (
        f"📋 {category_label}\n"
        f"{bar} {done}/{total} · {percent(done, total)}%\n\n"
        "Нажмите на задачу, чтобы открыть её."
    )

    if notice:
        text = f"{notice}\n\n{text}"

    kb = checklist_keyboard(items)
    await render(update, context, text, kb, message_id)

    return set_state(context, CHECKLIST_VIEW)


async def view_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data or ""

    await answer(query)

    user = update.effective_user
    if not user:
        return MAIN_MENU

    message_id = query.message.message_id if query.message else None

    if data.startswith(CB_ITEM_PREFIX):
        try:
            item_id = int(data.split(":", 1)[1])
        except (TypeError, ValueError):
            return await show_categories(update, context, message_id)

        item = get_item_by_id(user.id, item_id)

        if not item:
            return await show_current_checklist(update, context, message_id, notice="⚠️ Задача не найдена.")

        status_text = "✅ Выполнено" if item.get("completed") else "⚪️ Не выполнено"
        category_label = CATEGORY_NAMES.get(item.get("category"), item.get("category"))

        text = (
            "📌 Задача\n\n"
            f"{item.get('text')}\n\n"
            f"Статус: {status_text}\n"
            f"Категория: {category_label}"
        )

        kb = item_detail_keyboard(item_id, bool(item.get("completed")))
        await render(update, context, text, kb, message_id)

        return set_state(context, ITEM_DETAIL)

    if data == CB_BACK_CATEGORIES:
        return await show_categories(update, context, message_id)

    if data == CB_BACK_MENU:
        return await show_main_menu(update, context, message_id)

    return await show_current_checklist(update, context, message_id)


async def show_current_checklist(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
    notice: str | None = None,
) -> int:
    category = context.user_data.get("current_category")

    if not category:
        return await show_categories(update, context, message_id, notice)

    return await show_checklist(update, context, category, message_id, notice)


async def toggle_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data or ""

    user = update.effective_user
    if not user:
        return MAIN_MENU

    message_id = query.message.message_id if query.message else None

    if data.startswith(CB_TOGGLE_PREFIX):
        try:
            item_id = int(data.split(":", 1)[1])
        except (TypeError, ValueError):
            await answer(query)
            return await show_current_checklist(update, context, message_id)

        new_state = toggle_item(user.id, item_id)

        if new_state is None:
            await answer(query)
            return await show_current_checklist(update, context, message_id, notice="⚠️ Задача не найдена.")

        toast = "✅ Выполнено" if new_state else "↩️ Отменено"
        await answer(query, toast)

        item = get_item_by_id(user.id, item_id)

        if not item:
            return await show_current_checklist(update, context, message_id)

        status_text = "✅ Выполнено" if item.get("completed") else "⚪️ Не выполнено"
        category_label = CATEGORY_NAMES.get(item.get("category"), item.get("category"))

        text = (
            "📌 Задача\n\n"
            f"{item.get('text')}\n\n"
            f"Статус: {status_text}\n"
            f"Категория: {category_label}"
        )

        kb = item_detail_keyboard(item_id, bool(item.get("completed")))
        await render(update, context, text, kb, message_id)

        return set_state(context, ITEM_DETAIL)

    await answer(query)

    if data == CB_BACK_CATEGORIES:
        return await show_current_checklist(update, context, message_id)

    if data == CB_BACK_MENU:
        return await show_main_menu(update, context, message_id)

    return await show_current_checklist(update, context, message_id)


# =========================
# PROGRESS
# =========================

async def show_progress(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
    notice: str | None = None,
) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU

    summary = get_user_progress_summary(user.id)

    if summary is None:
        return await show_main_menu(update, context, message_id, notice="Сначала начните смену.")

    done, total, items, categories = summary

    if total == 0:
        text = "📊 Прогресс\n\nНа сегодня задач нет."
        kb = back_menu_keyboard()
    else:
        bar = progress_bar(done, total)
        pct = percent(done, total)

        lines = [
            "📊 Прогресс",
            "",
            f"{bar} {done}/{total} · {pct}%",
            "",
        ]

        for cat, stats in categories.items():
            cat_label = CATEGORY_NAMES.get(cat, cat)
            lines.append(f"{cat_label} · {stats['done']}/{stats['total']}")

        if done == total:
            lines.append("")
            lines.append("🎉 Все задачи выполнены!")
        else:
            undone = [item for item in items if not item.get("completed")]
            lines.append("")
            lines.append(f"Осталось: {len(undone)}")

        text = "\n".join(lines)
        kb = progress_keyboard()

    if notice:
        text = f"{notice}\n\n{text}"

    await render(update, context, text, kb, message_id)
    return set_state(context, PROGRESS_VIEW)


async def progress_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await answer(query)

    message_id = query.message.message_id if query.message else None
    return await show_main_menu(update, context, message_id)


# =========================
# END SHIFT
# =========================

async def show_end_confirm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU

    shift = get_current_shift(user.id)
    if not shift:
        return await show_main_menu(update, context, message_id, notice="Смена ещё не начата.")

    summary = get_user_progress_summary(user.id)

    text = "🏁 Завершить смену?\n\n"

    if summary is None:
        text += "Не удалось получить прогресс."
    else:
        done, total, items, categories = summary

        if total == 0:
            text += "На сегодня задач нет."
        else:
            bar = progress_bar(done, total)
            text += f"{bar} {done}/{total} · {percent(done, total)}%\n\n"

            if done < total:
                text += f"⚠️ Осталось задач: {total - done}."
            else:
                text += "🎉 Все задачи выполнены."

    kb = end_shift_keyboard()
    await render(update, context, text, kb, message_id)

    return set_state(context, END_SHIFT_CONFIRM)


async def end_shift_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data or ""

    await answer(query)

    user = update.effective_user
    if not user:
        return MAIN_MENU

    message_id = query.message.message_id if query.message else None

    if data == CB_END_SHIFT_CONFIRM:
        end_current_shift(user.id)
        return await show_main_menu(update, context, message_id, notice="✅ Смена завершена.")

    if data == CB_END_SHIFT_CANCEL:
        return await show_main_menu(update, context, message_id)

    return await show_end_confirm(update, context, message_id)


# =========================
# NOOP
# =========================

async def noop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await answer(query)
    return current_state(context)