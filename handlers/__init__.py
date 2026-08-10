from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes
from db.users import save_user, get_user
from config import ADMIN_IDS

# Импорты сотрудников (без изменений)
from .employee.handlers import (
    start_menu,
    main_menu_callback,
    location_selection,
    category_selection,
    checklist_action,
    progress_back,
    noop
)
from .employee.constants import (
    MAIN_MENU,
    SELECT_LOCATION,
    CHECKLIST_VIEW,
    PROGRESS_VIEW,
    CATEGORY_SELECT,
    CB_BACK_MAIN,
    CB_SHIFT_MARK,
    CB_CHECKLIST,
    CB_PROGRESS,
    CB_SHIFT_BAR,
    CB_SHIFT_KITCHEN,
    CB_ITEM_DONE,
    CB_ITEM_UNDO,
    CB_CATEGORY,
    CB_BACK_CATEGORIES
)

# Импорты админа (обновлённые)
from .admin.handlers import admin_start, admin_callback, admin_text_input
from .admin.constant import (
    ADMIN_MAIN,
    ADMIN_SHIFTS,
    ADMIN_SELECT_USER,
    ADMIN_SELECT_DATE,
    ADMIN_VIEW_PROGRESS,
    ADMIN_EDIT_MENU,
    ADMIN_ADD_ITEM,
    ADMIN_EDIT_ITEM,
    ADMIN_DELETE_ITEM,
    ADMIN_INPUT_TEXT,
    CB_ADMIN_SHIFTS,
    CB_ADMIN_PROGRESS,
    CB_ADMIN_EDIT,
    CB_ADMIN_BACK,
    CB_ADMIN_USER,
    CB_ADMIN_DATE,
    CB_ADMIN_EDIT_ACTION,
    CB_ADMIN_ADD,
    CB_ADMIN_EDIT_ITEM,
    CB_ADMIN_DELETE_ITEM,
    CB_ADMIN_CONFIRM_DELETE
)

async def start_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_router)],
        states={
            # Состояния для сотрудников (без изменений)
            MAIN_MENU: [
                CallbackQueryHandler(main_menu_callback, pattern=f"^{CB_SHIFT_MARK}$|^{CB_CHECKLIST}$|^{CB_PROGRESS}$|^{CB_BACK_MAIN}$")
            ],
            SELECT_LOCATION: [
                CallbackQueryHandler(location_selection, pattern=f"^{CB_SHIFT_BAR}$|^{CB_SHIFT_KITCHEN}$|^{CB_BACK_MAIN}$")
            ],
            CATEGORY_SELECT: [
                CallbackQueryHandler(category_selection, pattern=f"^{CB_CATEGORY}.*|^{CB_BACK_MAIN}$")
            ],
            CHECKLIST_VIEW: [
                CallbackQueryHandler(checklist_action, pattern=f"^{CB_ITEM_DONE}.*|^{CB_ITEM_UNDO}.*|^{CB_BACK_CATEGORIES}$|^{CB_BACK_MAIN}$"),
                CallbackQueryHandler(noop, pattern="^noop$")
            ],
            PROGRESS_VIEW: [
                CallbackQueryHandler(progress_back, pattern=f"^{CB_BACK_MAIN}$")
            ],
            # Состояния для админа (добавлены все новые)
            ADMIN_MAIN: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_SHIFTS}$|^{CB_ADMIN_PROGRESS}$|^{CB_ADMIN_EDIT}$")
            ],
            ADMIN_SHIFTS: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_BACK}$")
            ],
            ADMIN_SELECT_USER: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_USER}.*|^{CB_ADMIN_BACK}$")
            ],
            ADMIN_SELECT_DATE: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_DATE}.*|^{CB_ADMIN_BACK}$")
            ],
            ADMIN_VIEW_PROGRESS: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_BACK}$")
            ],
            ADMIN_EDIT_MENU: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_EDIT_ACTION}.*|^{CB_ADMIN_BACK}$")
            ],
            ADMIN_ADD_ITEM: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_BACK}$")
            ],
            ADMIN_EDIT_ITEM: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_EDIT_ITEM}.*|^{CB_ADMIN_BACK}$")
            ],
            ADMIN_DELETE_ITEM: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_DELETE_ITEM}.*|^{CB_ADMIN_CONFIRM_DELETE}.*|^{CB_ADMIN_BACK}$")
            ],
            ADMIN_INPUT_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_input),
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_BACK}$")
            ],
        },
        fallbacks=[CommandHandler("start", start_router)],
        per_user=True,
        per_chat=False,
    )
    app.add_handler(conv_handler)