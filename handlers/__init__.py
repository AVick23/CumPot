from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
)
from telegram import Update
from telegram.ext import ContextTypes

from db.users import save_user, get_user

# ===================== ИЗОЛИРОВАННЫЕ ПАКЕТЫ =====================
from .employee import get_employee_entry_point, register_employee_states
from .admin import get_admin_entry_point, register_admin_states


async def start_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Единая точка входа.
    Роутит пользователя к точке входа админа или сотрудника.
    """
    user = update.effective_user
    if not user:
        return ConversationHandler.END

    # Не берём имя из Telegram как основной профиль
    save_user(user.id, user.username, None, None)
    user_data = get_user(user.id)

    if user_data and user_data.get("is_admin"):
        admin_entry = get_admin_entry_point()
        return await admin_entry(update, context)

    employee_entry = get_employee_entry_point()
    return await employee_entry(update, context)


def register_handlers(app: Application):
    # Единый словарь состояний для всего бота
    states = {}

    # Заполняем состояния из изолированных пакетов
    register_employee_states(states)
    register_admin_states(states)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_router)],
        states=states,
        fallbacks=[CommandHandler("start", start_router)],
        per_user=True,
        per_chat=False,
        allow_reentry=True,
    )

    app.add_handler(conv_handler)