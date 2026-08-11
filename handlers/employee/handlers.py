import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from db.users import get_user, update_user_profile

from utils.time_utils import today_msk_str, time_msk_str
from utils.channel import send_photo_to_channel

from .constants import (
    ONBOARD_NAME,
    ONBOARD_POSITION,
    MAIN_MENU,
    CATEGORY_SELECT,
    CHECKLIST_VIEW,
    ITEM_DETAIL,
    PROGRESS_VIEW,
    AWAIT_TASK_PHOTO,
    CB_NOOP,
    CB_START_SHIFT,
    CB_CHECKLIST,
    CB_PROGRESS,
    CB_POSITION_PREFIX,
    CB_CATEGORY_PREFIX,
    CB_ITEM_PREFIX,
    CB_TOGGLE_PREFIX,
    CB_PHOTO_PREFIX,
    CB_VIEW_PHOTO_PREFIX,
    CB_PHOTO_CANCEL,
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
    photo_prompt_keyboard,
)

from .utils import (
    get_position_label,
    start_shift_for_user,
    get_current_shift,
    get_categories_stats,
    get_items_by_category,
    get_item_by_id,
    toggle_item,
    attach_photo_to_task,
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


async def answer(query, text: str | None = None, show_alert: bool = False) -> None:
    try:
        await query.answer(text or "", show_alert=show_alert)
    except Exception:
        pass


async def render(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup=None,
    message_id: int | None = None,
) -> int | None:
    """
    Если message_id передан — редактируем сообщение.
    Если нет — отправляем новое.
    """
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


async def cleanup_message(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int | None,
    message_id: int | None,
    fallback_text: str = "✅ Готово",
) -> None:
    """
    Удаляет служебное сообщение.
    Если удалить нельзя — редактирует его и убирает кнопки.
    """
    if not chat_id or not message_id:
        return

    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        return
    except Exception:
        pass

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=fallback_text,
            reply_markup=None,
        )
    except Exception:
        pass


def main_menu_text(user_db: dict, shift: dict | None) -> str:
    full_name = user_db.get("full_name") or "Сотрудник"

    if shift:
        shift_location_label = get_position_label(shift.get("location"))
        return (
            "🟢 Смена открыта\n"
            f"📍 {shift_location_label} · с {shift.get('start_time', '—')}\n\n"
            "Смена закроется автоматически после 00:00 по МСК.\n"
            "Выберите действие."
        )

    position_label = get_position_label(user_db.get("position"))

    return (
        f"👋 {full_name}\n"
        f"Ваша позиция: {position_label}\n\n"
        "Сейчас вы не на смене.\n"
        "Когда будете готовы, начните смену."
    )


def item_detail_text(item: dict) -> str:
    status_text = "✅ Выполнено" if item.get("completed") else "⚪️ Не выполнено"
    category_label = CATEGORY_NAMES.get(item.get("category"), item.get("category"))
    photo_text = "🖼 Фото прикреплено" if item.get("has_photo") else "🖼 Фото: нет"

    return (
        "📌 Задача\n\n"
        f"{item.get('text')}\n\n"
        f"Статус: {status_text}\n"
        f"Категория: {category_label}\n"
        f"{photo_text}"
    )


def build_photo_caption(user_id: int, item: dict) -> str:
    user_db = get_user(user_id)

    full_name = "Сотрудник"
    position_label = "—"

    if user_db:
        full_name = user_db.get("full_name") or "Сотрудник"
        position_label = get_position_label(user_db.get("position"))

    today = today_msk_str()
    now_time = time_msk_str()

    caption = (
        "📷 Фото к задаче\n\n"
        f"👤 {full_name}\n"
        f"📍 {position_label}\n"
        f"📅 {today}\n"
        f"🕒 {now_time}\n\n"
        f"Задача:\n{item.get('text')}"
    )

    if len(caption) > 1000:
        caption = caption[:1000] + "…"

    return caption


# =========================
# ONBOARDING
# =========================

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id if update.effective_chat else None
    if not chat_id:
        return set_state(context, ONBOARD_NAME)

    context.user_data.pop("onboarding_full_name", None)
    context.user_data.pop("onboarding_name_msg_id", None)
    context.user_data.pop("onboarding_position_msg_id", None)
    context.user_data.pop("await_photo", None)
    context.user_data.pop("current_category", None)

    text = (
        "👋 Добро пожаловать!\n\n"
        "Чтобы продолжить, укажите ваше ФИО полностью.\n\n"
        "Например:\n"
        "Иванов Иван Иванович"
    )

    msg = await context.bot.send_message(chat_id=chat_id, text=text)
    context.user_data["onboarding_name_msg_id"] = msg.message_id

    return set_state(context, ONBOARD_NAME)


async def ask_position(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id if update.effective_chat else None
    if not chat_id:
        return set_state(context, ONBOARD_POSITION)

    full_name = context.user_data.get("onboarding_full_name") or ""

    if full_name:
        text = (
            f"Приятно познакомиться, {full_name}!\n\n"
            "Теперь выберите, где вы работаете."
        )
    else:
        text = "Теперь выберите, где вы работаете."

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=position_keyboard(),
    )

    context.user_data["onboarding_position_msg_id"] = msg.message_id

    return set_state(context, ONBOARD_POSITION)


async def employee_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU

    user_db = get_user(user.id)

    context.user_data.pop("onboarding_full_name", None)
    context.user_data.pop("onboarding_name_msg_id", None)
    context.user_data.pop("onboarding_position_msg_id", None)
    context.user_data.pop("await_photo", None)
    context.user_data.pop("current_category", None)

    if not user_db or not (user_db.get("full_name") or "").strip():
        return await ask_name(update, context)

    if not (user_db.get("position") or "").strip():
        context.user_data["onboarding_full_name"] = user_db.get("full_name")
        return await ask_position(update, context)

    return await show_main_menu(update, context, None)


async def onboarding_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return set_state(context, ONBOARD_NAME)

    if not update.message.text:
        return await onboarding_wrong_type_name(update, context)

    chat_id = update.effective_chat.id if update.effective_chat else None

    raw_text = (update.message.text or "").strip()
    full_name = " ".join(raw_text.split())

    if len(full_name) < 5 or len(full_name.split()) < 2:
        await update.message.reply_text(
            "⚠️ Пожалуйста, укажите ФИО полностью: минимум фамилия и имя.\n\n"
            "Например:\n"
            "Иванов Иван Иванович"
        )
        return set_state(context, ONBOARD_NAME)

    if len(full_name) > FULL_NAME_LIMIT:
        await update.message.reply_text(
            f"⚠️ Слишком длинно. Максимум {FULL_NAME_LIMIT} символов.\n\n"
            "Пожалуйста, укажите ФИО ещё раз."
        )
        return set_state(context, ONBOARD_NAME)

    await cleanup_message(
        context,
        chat_id,
        context.user_data.get("onboarding_name_msg_id"),
        "✅ ФИО получено",
    )

    context.user_data["onboarding_full_name"] = full_name

    return await ask_position(update, context)


async def onboarding_wrong_type_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ Пожалуйста, отправьте ФИО обычным текстовым сообщением.",
        )

    return set_state(context, ONBOARD_NAME)


async def onboarding_callback_guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await answer(query, "Сначала введите ФИО текстом")
    return set_state(context, ONBOARD_NAME)


async def onboarding_position(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data or ""

    user = update.effective_user
    if not user:
        return MAIN_MENU

    if not data.startswith(CB_POSITION_PREFIX):
        return await onboarding_position_guard(update, context)

    position = data.split(":", 1)[1]

    if position not in LOCATIONS:
        await answer(query, "Выберите одну из позиций")
        return set_state(context, ONBOARD_POSITION)

    user_db = get_user(user.id)
    full_name = context.user_data.get("onboarding_full_name") or (user_db.get("full_name") if user_db else None)

    if not full_name:
        return await ask_name(update, context)

    update_user_profile(user.id, full_name=full_name, position=position)

    chat_id = update.effective_chat.id if update.effective_chat else None

    message_id = None
    if query.message:
        message_id = query.message.message_id
    else:
        message_id = context.user_data.get("onboarding_position_msg_id")

    await cleanup_message(context, chat_id, message_id, "✅ Позиция сохранена")

    context.user_data.pop("onboarding_full_name", None)
    context.user_data.pop("onboarding_name_msg_id", None)
    context.user_data.pop("onboarding_position_msg_id", None)

    return await show_main_menu(
        update,
        context,
        None,
        notice="✅ Профиль сохранён. Теперь можно начинать смену."
    )


async def onboarding_position_guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await answer(query, "Выберите одну из позиций")
    return set_state(context, ONBOARD_POSITION)


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
        return await ask_name(update, context)

    if not (user_db.get("position") or "").strip():
        context.user_data["onboarding_full_name"] = user_db.get("full_name")
        return await ask_position(update, context)

    context.user_data.pop("current_category", None)
    context.user_data.pop("await_photo", None)

    shift = get_current_shift(user.id)
    text = main_menu_text(user_db, shift)

    if notice:
        text = f"{notice}\n\n{text}"

    kb = main_menu_keyboard(has_shift=bool(shift))

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


async def show_item_detail(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    item_id: int,
    message_id: int | None = None,
    notice: str | None = None,
) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU

    item = get_item_by_id(user.id, item_id)

    if not item:
        return await show_current_checklist(update, context, message_id, notice="⚠️ Задача не найдена.")

    text = item_detail_text(item)

    if notice:
        text = f"{notice}\n\n{text}"

    kb = item_detail_keyboard(
        item_id,
        bool(item.get("completed")),
        bool(item.get("has_photo")),
    )

    await render(update, context, text, kb, message_id)
    return set_state(context, ITEM_DETAIL)


async def send_new_item_detail(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    item_id: int,
    notice: str | None = None,
) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU

    chat_id = update.effective_chat.id if update.effective_chat else None
    if not chat_id:
        return MAIN_MENU

    item = get_item_by_id(user.id, item_id)

    if not item:
        return await show_main_menu(update, context, None, notice="⚠️ Задача не найдена.")

    text = item_detail_text(item)

    if notice:
        text = f"{notice}\n\n{text}"

    kb = item_detail_keyboard(
        item_id,
        bool(item.get("completed")),
        bool(item.get("has_photo")),
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=kb,
    )

    return set_state(context, ITEM_DETAIL)


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

        return await show_item_detail(update, context, item_id, message_id)

    if data == CB_BACK_CATEGORIES:
        return await show_categories(update, context, message_id)

    if data == CB_BACK_MENU:
        return await show_main_menu(update, context, message_id)

    return await show_current_checklist(update, context, message_id)


# =========================
# TOGGLE + PHOTO CALLBACKS
# =========================

async def show_photo_prompt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    item_id: int,
) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU

    chat_id = update.effective_chat.id if update.effective_chat else None
    if not chat_id:
        return MAIN_MENU

    item = get_item_by_id(user.id, item_id)

    if not item:
        return await show_current_checklist(update, context, None, notice="⚠️ Задача не найдена.")

    text = (
        "📷 Отправьте фото одним сообщением.\n\n"
        f"Задача:\n{item.get('text')}\n\n"
        "После загрузки фото будет сохранено в служебный канал."
    )

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=photo_prompt_keyboard(),
    )

    context.user_data["await_photo"] = {
        "item_id": item_id,
        "mark_done": not bool(item.get("completed")),
        "prompt_message_id": msg.message_id,
    }

    return set_state(context, AWAIT_TASK_PHOTO)


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

        return await show_item_detail(update, context, item_id, message_id)

    if data.startswith(CB_PHOTO_PREFIX):
        try:
            item_id = int(data.split(":", 1)[1])
        except (TypeError, ValueError):
            await answer(query)
            return await show_current_checklist(update, context, message_id)

        item = get_item_by_id(user.id, item_id)

        if not item:
            await answer(query)
            return await show_current_checklist(update, context, message_id, notice="⚠️ Задача не найдена.")

        await answer(query)
        return await show_photo_prompt(update, context, item_id)

    if data.startswith(CB_VIEW_PHOTO_PREFIX):
        try:
            item_id = int(data.split(":", 1)[1])
        except (TypeError, ValueError):
            await answer(query)
            return await show_current_checklist(update, context, message_id)

        item = get_item_by_id(user.id, item_id)

        if not item or not item.get("photo_file_id"):
            await answer(query, "Фото не найдено")
            return await show_item_detail(update, context, item_id, message_id)

        chat_id = update.effective_chat.id if update.effective_chat else None

        if chat_id:
            try:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=item["photo_file_id"],
                )
                await answer(query, "Фото отправлено выше")
            except Exception as e:
                logger.warning("View photo failed: %s", e)
                await answer(query, "Не удалось отправить фото")
        else:
            await answer(query, "Не удалось отправить фото")

        return set_state(context, ITEM_DETAIL)

    await answer(query)

    if data == CB_BACK_CATEGORIES:
        return await show_current_checklist(update, context, message_id)

    if data == CB_BACK_MENU:
        return await show_main_menu(update, context, message_id)

    return await show_current_checklist(update, context, message_id)


# =========================
# PHOTO INPUT STATE
# =========================

async def photo_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU

    chat_id = update.effective_chat.id if update.effective_chat else None
    if not chat_id:
        return MAIN_MENU

    meta = context.user_data.get("await_photo")

    if not meta:
        return await show_main_menu(update, context, None, notice="Начните заново с /start.")

    if not update.message or not update.message.photo:
        return await photo_wrong_type(update, context)

    item_id = meta.get("item_id")
    mark_done = bool(meta.get("mark_done"))
    prompt_message_id = meta.get("prompt_message_id")

    item = get_item_by_id(user.id, item_id)

    if not item:
        context.user_data.pop("await_photo", None)
        return await show_main_menu(update, context, None, notice="⚠️ Задача не найдена.")

    photo_file_id = update.message.photo[-1].file_id
    caption = build_photo_caption(user.id, item)

    try:
        channel_message_id = await send_photo_to_channel(context, photo_file_id, caption)
    except Exception as e:
        logger.error("Failed to send photo to channel: %s", e)

        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "⚠️ Не удалось загрузить фото в канал.\n\n"
                "Проверьте, что бот добавлен в канал администратором и имеет право публикации сообщений.\n\n"
                "Попробуйте отправить фото ещё раз."
            ),
        )

        return set_state(context, AWAIT_TASK_PHOTO)

    attach_photo_to_task(
        user_id=user.id,
        item_id=item_id,
        file_id=photo_file_id,
        channel_message_id=channel_message_id,
        mark_done=mark_done,
    )

    context.user_data.pop("await_photo", None)

    await cleanup_message(context, chat_id, prompt_message_id, "✅ Фото получено")

    if mark_done:
        notice = "🎉 Молодец! Задача выполнена, фото сохранено."
    else:
        notice = "🎉 Молодец! Фото сохранено."

    return await send_new_item_detail(update, context, item_id, notice)


async def photo_wrong_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id if update.effective_chat else None

    if chat_id:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "⚠️ Пожалуйста, отправьте именно фото.\n\n"
                "Если хотите отменить прикрепление фото, нажмите кнопку «Отмена» под запросом фото."
            ),
        )

    return set_state(context, AWAIT_TASK_PHOTO)


async def photo_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await answer(query)

    user = update.effective_user
    if not user:
        return MAIN_MENU

    chat_id = update.effective_chat.id if update.effective_chat else None

    meta = context.user_data.get("await_photo") or {}

    item_id = meta.get("item_id")
    prompt_message_id = meta.get("prompt_message_id")

    if not prompt_message_id and query.message:
        prompt_message_id = query.message.message_id

    context.user_data.pop("await_photo", None)

    await cleanup_message(context, chat_id, prompt_message_id, "❌ Отменено")

    if item_id:
        return await send_new_item_detail(update, context, item_id, notice="Отменено.")

    return await show_main_menu(update, context, None)


async def photo_state_guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await answer(query, "Сначала отправьте фото или нажмите «Отмена»")
    return set_state(context, AWAIT_TASK_PHOTO)


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
# NOOP
# =========================

async def noop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await answer(query)
    return current_state(context)