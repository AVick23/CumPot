import logging
from telegram import Update
from telegram.ext import ContextTypes

from db.users import get_user, update_user_profile
from db.shifts import start_shift, get_active_shift

from .constants import (
    ONBOARD_NAME,
    ONBOARD_POSITION,
    MAIN_MENU,
    CB_START_SHIFT,
    CB_CHECKLIST,
    CB_PROGRESS,
    CB_BACK_MENU,
    CB_POSITION_PREFIX,
    LOCATIONS,
    FULL_NAME_LIMIT,
)
from .keyboards import position_keyboard, main_menu_keyboard, back_menu_keyboard
from .utils import (
    main_menu_text,
    render,
    cleanup_message,
    answer,
    set_state,
    get_position_label,
)

logger = logging.getLogger(__name__)


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (локальные) ====================

def start_shift_for_user(user_id: int) -> bool:
    user = get_user(user_id)
    if not user:
        return False
    position = user.get("position")
    if position not in LOCATIONS:
        return False
    start_shift(user_id, position)
    return True


def get_current_shift(user_id: int) -> dict | None:
    return get_active_shift(user_id)


# ==================== ЭКРАНЫ ====================

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id
    if not chat_id:
        return set_state(context, ONBOARD_NAME)

    context.user_data.pop("onboarding_full_name", None)
    context.user_data.pop("onboarding_name_msg_id", None)
    context.user_data.pop("onboarding_position_msg_id", None)

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
    chat_id = update.effective_chat.id
    if not chat_id:
        return set_state(context, ONBOARD_POSITION)

    full_name = context.user_data.get("onboarding_full_name") or ""

    if full_name:
        text = f"Приятно познакомиться, {full_name}!\n\nТеперь выберите, где вы работаете."
    else:
        text = "Теперь выберите, где вы работаете."

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=position_keyboard(),
    )

    context.user_data["onboarding_position_msg_id"] = msg.message_id

    return set_state(context, ONBOARD_POSITION)


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


# ==================== ОБРАБОТЧИКИ ====================

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data or ""

    await answer(query)

    user = update.effective_user
    if not user:
        return MAIN_MENU

    message_id = query.message.message_id if query.message else None

    if data == CB_START_SHIFT:
        if get_current_shift(user.id):
            return await show_main_menu(update, context, message_id, notice="Вы уже на смене.")

        user_db = get_user(user.id)
        if not user_db or not user_db.get("position"):
            return await employee_start(update, context)

        started = start_shift_for_user(user.id)

        if not started:
            return await show_main_menu(update, context, message_id, notice="⚠️ Не удалось начать смену.")

        return await show_main_menu(update, context, message_id, notice="✅ Смена открыта. Хорошей смены!")

    if data == CB_CHECKLIST:
        # Перенаправление в пакет checklists
        from ..checklists.handlers import show_categories
        return await show_categories(update, context, message_id)

    if data == CB_PROGRESS:
        from ..checklists.handlers import show_progress
        return await show_progress(update, context, message_id)

    if data == CB_BACK_MENU:
        return await show_main_menu(update, context, message_id)

    return await show_main_menu(update, context, message_id)


# ==================== ОНБОРДИНГ ====================

async def onboarding_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return await onboarding_wrong_type_name(update, context)

    chat_id = update.effective_chat.id

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

    chat_id = update.effective_chat.id

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