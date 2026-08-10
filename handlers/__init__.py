from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler
from telegram import Update
from telegram.ext import ContextTypes
from db.users import save_user, get_user
from config import ADMIN_IDS

# Импортируем функции и константы из папок employee и admin
from .employee.handlers import (
    start_menu,
    main_menu_callback,
    location_selection,
    checklist_action,
    progress_back,
    noop
)
from .employee.constants import (
    MAIN_MENU,
    SELECT_LOCATION,
    CHECKLIST_VIEW,
    PROGRESS_VIEW,
    CB_BACK_MAIN,
    CB_SHIFT_MARK,
    CB_CHECKLIST,
    CB_PROGRESS,
    CB_SHIFT_BAR,
    CB_SHIFT_KITCHEN,
    CB_ITEM_DONE,
    CB_ITEM_UNDO
)

from .admin.handlers import admin_start, admin_callback
from .admin.constant import (
    ADMIN_MAIN,
    ADMIN_SHIFTS,
    ADMIN_PROGRESS,
    ADMIN_EDIT,
    CB_ADMIN_SHIFTS,
    CB_ADMIN_PROGRESS,
    CB_ADMIN_EDIT,
    CB_ADMIN_BACK
)

async def start_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Единый обработчик команды /start – определяет роль и передаёт управление нужному состоянию."""
    user = update.effective_user
    tg_id = user.id
    save_user(tg_id, user.username, user.first_name, user.last_name)
    user_data = get_user(tg_id)

    if user_data and user_data['is_admin']:
        await admin_start(update, context)
        return ADMIN_MAIN
    else:
        await start_menu(update, context)
        return MAIN_MENU

def register_handlers(app: Application):
    """Регистрирует единый ConversationHandler для всех ролей."""
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_router)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(
                    main_menu_callback,
                    pattern=f"^{CB_SHIFT_MARK}$|^{CB_CHECKLIST}$|^{CB_PROGRESS}$|^{CB_BACK_MAIN}$"
                ),
            ],
            SELECT_LOCATION: [
                CallbackQueryHandler(
                    location_selection,
                    pattern=f"^{CB_SHIFT_BAR}$|^{CB_SHIFT_KITCHEN}$|^{CB_BACK_MAIN}$"
                ),
            ],
            CHECKLIST_VIEW: [
                CallbackQueryHandler(
                    checklist_action,
                    pattern=f"^{CB_ITEM_DONE}.*|^{CB_ITEM_UNDO}.*|^{CB_BACK_MAIN}$"
                ),
                CallbackQueryHandler(noop, pattern="^noop$"),  # игнорируем заголовки категорий
            ],
            PROGRESS_VIEW: [
                CallbackQueryHandler(progress_back, pattern=f"^{CB_BACK_MAIN}$"),
            ],
            ADMIN_MAIN: [
                CallbackQueryHandler(
                    admin_callback,
                    pattern=f"^{CB_ADMIN_SHIFTS}$|^{CB_ADMIN_PROGRESS}$|^{CB_ADMIN_EDIT}$"
                ),
            ],
            ADMIN_SHIFTS: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_BACK}$"),
            ],
            ADMIN_PROGRESS: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_BACK}$"),
            ],
            ADMIN_EDIT: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_BACK}$"),
            ],
        },
        fallbacks=[CommandHandler("start", start_router)],
        per_user=True,
        per_chat=False,
    )
    app.add_handler(conv_handler)