import logging
from telegram import Update
from telegram.ext import ContextTypes
from .utils import start_shift_for_user, get_current_shift, end_shift_for_user
from .keyboards import shift_control_keyboard
from .constants import LOCATIONS

logger = logging.getLogger(__name__)


async def shift_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обработчик команды начала смены.
    Возвращает состояние (можно использовать для перехода).
    """
    user = update.effective_user
    if not user:
        return -1

    chat_id = update.effective_chat.id
    if not chat_id:
        return -1

    if get_current_shift(user.id):
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Вы уже на смене."
        )
        return 0

    success = start_shift_for_user(user.id)
    if success:
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Смена открыта. Хорошей смены!"
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Не удалось начать смену. Убедитесь, что у вас указана позиция."
        )
    return 0


async def shift_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обработчик завершения смены.
    """
    user = update.effective_user
    if not user:
        return -1

    chat_id = update.effective_chat.id
    if not chat_id:
        return -1

    success = end_shift_for_user(user.id)
    if success:
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Смена завершена. Отдыхайте!"
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ У вас нет активной смены."
        )
    return 0


async def shift_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Показывает статус текущей смены.
    """
    user = update.effective_user
    if not user:
        return -1

    chat_id = update.effective_chat.id
    if not chat_id:
        return -1

    shift = get_current_shift(user.id)
    if shift:
        location_label = get_position_label(shift.get("location"))
        text = (
            "🟢 Смена активна\n"
            f"📍 {location_label}\n"
            f"🕒 Начало: {shift.get('start_time', '—')}"
        )
    else:
        text = "🔴 Смены нет. Начните смену, чтобы получить доступ к задачам."

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=shift_control_keyboard(bool(shift))
    )
    return 0