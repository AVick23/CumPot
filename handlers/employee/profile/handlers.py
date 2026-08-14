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
from .utils import format_date, format_phone

from ..menu.utils import render, answer, set_state, get_current_state

logger = logging.getLogger(__name__)

# Состояние главного меню (для возврата)
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
        await render(update, context, "Ошибка загрузки профиля.", None, message_id)
        return MAIN_MENU_STATE

    # Форматируем данные для отображения
    full_name = user_data.get("full_name") or "—"
    phone = format_phone(user_data.get("phone"))
    birthday = format_date(user_data.get("birthday"))
    address = user_data.get("address") or "—"
    responsibilities = user_data.get("responsibilities") or "—"
    position = user_data.get("position") or "—"

    # Используем HTML-теги для жирного шрифта
    text = (
        "👤 <b>Мой профиль</b>\n\n"
        f"<b>ФИО:</b> {full_name}\n"
        f"<b>Телефон:</b> {phone}\n"
        f"<b>День рождения:</b> {birthday}\n"
        f"<b>Адрес:</b> {address}\n"
        f"<b>Обязанности:</b> {responsibilities}\n"
        f"<b>Позиция:</b> {position}\n"
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

    # Обработка выбора поля для редактирования
    if data in EDIT_FIELD_MAP:
        field_name, state, prompt = EDIT_FIELD_MAP[data]

        # Сохраняем в context, какое поле редактируем
        context.user_data["profile_edit_field"] = field_name

        # Показываем сообщение с запросом ввода
        text = f"✏️ Редактирование <b>{FIELD_LABELS.get(field_name, field_name)}</b>\n\n{prompt}"
        kb = profile_edit_keyboard()
        await render(update, context, text, kb, message_id, parse_mode='HTML')
        await answer(query)

        return set_state(context, state)

    # Назад в меню
    if data == CB_PROFILE_BACK:
        from ..menu.handlers import show_main_menu
        await answer(query)
        return await show_main_menu(update, context, message_id)

    # Отмена редактирования
    if data == CB_PROFILE_CANCEL:
        await answer(query, "Редактирование отменено")
        context.user_data.pop("profile_edit_field", None)
        return await show_profile(update, context, message_id, notice="Редактирование отменено")

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

    # Валидация для позиции
    if field_name == "position":
        if text not in ("bar", "kitchen"):
            await update.message.reply_text(
                "⚠️ Позиция может быть только 'bar' или 'kitchen'.\n"
                "Пожалуйста, введите корректное значение."
            )
            return get_current_state(context)

    # Обновляем профиль
    update_user_profile(user.id, **{field_name: text})

    # Очищаем контекст
    context.user_data.pop("profile_edit_field", None)

    # Возвращаемся в просмотр профиля
    chat_id = update.effective_chat.id
    if chat_id:
        await update.message.reply_text("✅ Данные обновлены!")

    # Показываем обновлённый профиль (отправляем новое сообщение, так как старое могло быть с клавиатурой)
    return await show_profile(update, context, notice="✅ Профиль обновлён")