import logging
import json
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes

from db.profile import add_taxi_expense, get_taxi_expenses, get_taxi_summary
from db.users import get_user
from utils.channel import send_media_group_to_channel
from utils.time_utils import today_msk_str

from .constants import (
    TAXI_MENU,
    TAXI_ADD_AMOUNT,
    TAXI_ADD_PHOTO,
    TAXI_HISTORY,
    CB_TAXI_ADD,
    CB_TAXI_HISTORY,
    CB_TAXI_BACK,
    CB_TAXI_CANCEL,
)
from .keyboards import taxi_menu_keyboard, taxi_cancel_keyboard, taxi_history_keyboard
from .utils import render, answer, set_state, get_current_state, format_amount, cleanup_message

logger = logging.getLogger(__name__)
MAIN_MENU_STATE = 3


# ==================== ОСНОВНОЙ ЭКРАН ====================
async def show_taxi_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
    notice: str | None = None,
) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU_STATE

    # Проверим, есть ли активная смена (можно опционально)
    # Но так как кнопка появляется только при активной смене, можно не проверять.

    text = "🚕 **Такси**\n\nВы можете добавить расход на такси или посмотреть историю."
    if notice:
        text = f"{notice}\n\n{text}"

    kb = taxi_menu_keyboard()
    await render(update, context, text, kb, message_id)
    return set_state(context, TAXI_MENU)


# ==================== ДОБАВЛЕНИЕ РАСХОДА ====================
async def taxi_add_amount(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int | None = None) -> int:
    text = (
        "➕ **Добавление расхода на такси**\n\n"
        "Введите сумму в рублях (например, 350.50).\n\n"
        "После этого прикрепите фото чека или скриншот."
    )
    kb = taxi_cancel_keyboard()
    await render(update, context, text, kb, message_id)
    return set_state(context, TAXI_ADD_AMOUNT)


async def taxi_add_photo(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int | None = None) -> int:
    amount = context.user_data.get("taxi_amount")
    if not amount:
        await render(update, context, "⚠️ Сумма не указана. Начните заново.", None, message_id)
        return await show_taxi_menu(update, context, message_id)

    text = (
        f"➕ **Добавление расхода на такси**\n\n"
        f"Сумма: {format_amount(amount)}\n\n"
        "Теперь отправьте фото чека или скриншот.\n"
        "Можно отправить несколько фото (альбомом)."
    )
    kb = taxi_cancel_keyboard()
    await render(update, context, text, kb, message_id)
    return set_state(context, TAXI_ADD_PHOTO)


# ==================== ИСТОРИЯ ====================
async def taxi_history(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU_STATE

    # За последние 30 дней
    date_to = today_msk_str()
    date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    expenses = get_taxi_expenses(user.id, date_from, date_to)
    summary = get_taxi_summary(user.id, date_from, date_to)

    lines = [
        "📋 **История такси (за 30 дней)**",
        f"Всего записей: {summary['count']}, сумма: {format_amount(summary['total'])}",
        ""
    ]

    if expenses:
        for exp in expenses[:10]:  # показываем последние 10
            date = exp.get("date", "—")
            amount = exp.get("amount", 0)
            lines.append(f"🗓 {date} — {format_amount(amount)}")
    else:
        lines.append("Нет записей за этот период.")

    text = "\n".join(lines)
    kb = taxi_history_keyboard()
    await render(update, context, text, kb, message_id)
    return set_state(context, TAXI_HISTORY)


# ==================== ОБРАБОТЧИКИ CALLBACK ====================
async def taxi_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data or ""
    message_id = query.message.message_id if query.message else None

    user = update.effective_user
    if not user:
        return MAIN_MENU_STATE

    await answer(query)

    if data == CB_TAXI_ADD:
        return await taxi_add_amount(update, context, message_id)

    if data == CB_TAXI_HISTORY:
        return await taxi_history(update, context, message_id)

    if data == CB_TAXI_BACK:
        # Возвращаемся в главное меню
        from ..menu.handlers import show_main_menu
        return await show_main_menu(update, context, message_id)

    if data == CB_TAXI_CANCEL:
        context.user_data.pop("taxi_amount", None)
        context.user_data.pop("taxi_photos", None)
        return await show_taxi_menu(update, context, message_id, notice="Отменено")

    return await show_taxi_menu(update, context, message_id)


# ==================== ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ (сумма) ====================
async def taxi_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU_STATE

    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("⚠️ Введите сумму цифрами.")
        return get_current_state(context)

    # Парсим сумму
    try:
        # Заменяем запятую на точку
        amount_str = text.replace(",", ".")
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной")
    except ValueError:
        await update.message.reply_text("⚠️ Некорректная сумма. Введите число, например 350.50")
        return get_current_state(context)

    # Сохраняем сумму в контекст и переходим к запросу фото
    context.user_data["taxi_amount"] = amount
    # Удаляем предыдущее сообщение с запросом (если есть)
    chat_id = update.effective_chat.id
    await cleanup_message(context, chat_id, context.user_data.get("taxi_prompt_msg_id"))

    # Отправляем новое сообщение с запросом фото
    return await taxi_add_photo(update, context)


# ==================== ОБРАБОТЧИК ФОТО ====================
async def taxi_photo_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU_STATE

    chat_id = update.effective_chat.id
    if not chat_id:
        return MAIN_MENU_STATE

    amount = context.user_data.get("taxi_amount")
    if not amount:
        await update.message.reply_text("⚠️ Сумма не найдена. Начните заново.")
        return await show_taxi_menu(update, context)

    # Собираем все медиа из сообщения (если альбом)
    media_items = []
    if update.message.photo:
        # Одиночное фото
        media_items.append({"type": "photo", "file_id": update.message.photo[-1].file_id})
    elif update.message.media_group_id:
        # Альбом – сложнее, но мы будем обрабатывать как одиночное, т.к. альбом приходит частями.
        # Пока обрабатываем только первый файл, но можно доработать через буфер.
        # Для простоты: принимаем только одно фото (или первую часть альбома)
        if update.message.photo:
            media_items.append({"type": "photo", "file_id": update.message.photo[-1].file_id})
        else:
            await update.message.reply_text("⚠️ Отправьте фото или несколько фото альбомом.")
            return get_current_state(context)
    else:
        await update.message.reply_text("⚠️ Отправьте фото.")
        return get_current_state(context)

    if not media_items:
        await update.message.reply_text("⚠️ Не удалось распознать фото. Попробуйте ещё раз.")
        return get_current_state(context)

    # Отправляем фото в канал
    caption = f"🚕 Такси: {format_amount(amount)}"
    try:
        channel_message_ids = await send_media_group_to_channel(context, media_items, caption)
    except Exception as e:
        logger.error("Ошибка отправки фото такси в канал: %s", e)
        await update.message.reply_text("⚠️ Не удалось сохранить фото. Попробуйте позже.")
        return get_current_state(context)

    # Сохраняем запись в БД
    date = today_msk_str()
    photo_file_ids = [item.get("file_id") for item in media_items]
    add_taxi_expense(
        user_id=user.id,
        date=date,
        amount=amount,
        photo_file_ids=photo_file_ids,
        photo_channel_message_ids=channel_message_ids
    )

    # Очищаем контекст
    context.user_data.pop("taxi_amount", None)
    await cleanup_message(context, chat_id, context.user_data.get("taxi_prompt_msg_id"))

    await update.message.reply_text("✅ Расход на такси сохранён!")

    # Возвращаемся в меню такси
    return await show_taxi_menu(update, context, notice="✅ Расход добавлен")