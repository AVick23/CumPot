import logging
from telegram import Update
from telegram.ext import ContextTypes

from db.profile import get_user_profile, update_user_profile
from db.users import get_user
from utils.time_utils import today_msk_str

from .constants import (
    PROFILE_VIEW,
    PROFILE_EDIT_NAME,
    PROFILE_EDIT_PHONE,
    PROFILE_EDIT_BIRTHDAY,
    PROFILE_EDIT_ADDRESS,
    PROFILE_EDIT_RESPONSIBILITIES,
    PROFILE_EDIT_POSITION,
    CB_PROFILE_BACK,
    CB_PROFILE_CANCEL,
    FIELD_LABELS,
    EDIT_FIELD_MAP,
)
from .keyboards import profile_view_keyboard, profile_edit_keyboard
from .utils import format_date, format_phone, validate_phone, validate_date, validate_position

from ..menu.utils import render, answer, set_state, get_current_state

logger = logging.getLogger(__name__)

MAIN_MENU_STATE = 3


# ==================== ОСНОВНОЙ ЭКРАН ====================
async def show_profile(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
    notice: str | None = None,
) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU_STATE

    user_data = get_user_profile(user.id)
    if not user_data:
        await render(update, context, "⚠️ Ошибка загрузки профиля.", None, message_id)
        return MAIN_MENU_STATE

    # Сбор данных с форматированием
    full_name = user_data.get("full_name") or "—"
    phone = format_phone(user_data.get("phone"))
    birthday = format_date(user_data.get("birthday"))
    address = user_data.get("address") or "—"
    responsibilities = user_data.get("responsibilities") or "—"
    position = user_data.get("position") or "—"

    # Стильный вывод с разделителями и иконками
    text = (
        "👤 <b>Мой профиль</b>\n\n"
        f"<b>{FIELD_LABELS['full_name']}</b>  {full_name}\n"
        f"<b>{FIELD_LABELS['phone']}</b>  {phone}\n"
        f"<b>{FIELD_LABELS['birthday']}</b>  {birthday}\n"
        f"<b>{FIELD_LABELS['address']}</b>  {address}\n"
        f"<b>{FIELD_LABELS['responsibilities']}</b>  {responsibilities}\n"
        f"<b>{FIELD_LABELS['position']}</b>  {position}\n"
        "\n🔄 Нажмите на поле, чтобы изменить."
    )
    if notice:
        text = f"{notice}\n\n{text}"

    kb = profile_view_keyboard(user_data)
    await render(update, context, text, kb, message_id, parse_mode='HTML')
    return set_state(context, PROFILE_VIEW)


# ==================== ОБРАБОТЧИКИ CALLBACK ====================
async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data or ""
    message_id = query.message.message_id if query.message else None

    user = update.effective_user
    if not user:
        return MAIN_MENU_STATE

    # Редактирование поля
    if data in EDIT_FIELD_MAP:
        field_name, state, prompt = EDIT_FIELD_MAP[data]
        context.user_data["profile_edit_field"] = field_name

        # Показываем текущее значение для удобства
        user_data = get_user_profile(user.id) or {}
        current_value = user_data.get(field_name) or "не задано"

        text = (
            f"✏️ <b>Редактирование</b>\n\n"
            f"<b>{FIELD_LABELS.get(field_name, field_name)}</b>\n"
            f"Текущее значение: <i>{current_value}</i>\n\n"
            f"{prompt}"
        )
        kb = profile_edit_keyboard()
        await render(update, context, text, kb, message_id, parse_mode='HTML')
        await answer(query)
        return set_state(context, state)

    # Назад в главное меню
    if data == CB_PROFILE_BACK:
        from ..menu.handlers import show_main_menu
        await answer(query)
        return await show_main_menu(update, context, message_id)

    # Отмена редактирования
    if data == CB_PROFILE_CANCEL:
        await answer(query, "Редактирование отменено", show_alert=True)
        context.user_data.pop("profile_edit_field", None)
        return await show_profile(update, context, message_id, notice="✅ Редактирование отменено")

    # Fallback
    await answer(query)
    return await show_profile(update, context, message_id)


# ==================== ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ ====================
async def profile_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU_STATE

    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("⚠️ Текст не может быть пустым. Попробуйте ещё раз.")
        return get_current_state(context)

    field_name = context.user_data.get("profile_edit_field")
    if not field_name:
        await update.message.reply_text("⚠️ Ошибка: не выбрано поле для редактирования. Начните заново.")
        return MAIN_MENU_STATE

    # --- Валидация в зависимости от поля ---
    error = None
    if field_name == "phone":
        if not validate_phone(text):
            error = (
                "⚠️ Неверный формат телефона.\n"
                "Используйте международный формат, например: +79161234567"
            )
    elif field_name == "birthday":
        if not validate_date(text):
            error = (
                "⚠️ Неверный формат даты.\n"
                "Используйте ГГГГ-ММ-ДД, например: 1990-05-20"
            )
    elif field_name == "position":
        if not validate_position(text):
            error = (
                "⚠️ Позиция может быть только 'bar' или 'kitchen'.\n"
                "Введите корректное значение."
            )

    if error:
        await update.message.reply_text(error)
        return get_current_state(context)

    # --- Обновление ---
    try:
        update_user_profile(user.id, **{field_name: text})
        context.user_data.pop("profile_edit_field", None)

        # Уведомление об успехе
        await update.message.reply_text("✅ Данные успешно обновлены!")

        # Показываем обновлённый профиль (отправляем новое сообщение)
        return await show_profile(update, context, notice="✅ Профиль обновлён")

    except Exception as e:
        logger.error("Ошибка обновления профиля: %s", e)
        await update.message.reply_text("⚠️ Произошла ошибка при сохранении. Попробуйте позже.")
        return get_current_state(context)