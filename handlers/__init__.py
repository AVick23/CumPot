from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes
from db.users import save_user, get_user
from config import ADMIN_IDS

# Импорты сотрудников (обновлены: checklist_action заменён на view_item и toggle_item)
from .employee.handlers import (
    start_menu,
    main_menu_callback,
    location_selection,
    category_selection,
    view_item,          # вместо checklist_action
    toggle_item,        # вместо checklist_action
    progress_back,
    noop
)
from .employee.constants import (
    MAIN_MENU,
    SELECT_LOCATION,
    CHECKLIST_VIEW,
    PROGRESS_VIEW,
    CATEGORY_SELECT,
    ITEM_DETAIL,        # новое состояние
    CB_BACK_MAIN,
    CB_SHIFT_MARK,
    CB_CHECKLIST,
    CB_PROGRESS,
    CB_SHIFT_BAR,
    CB_SHIFT_KITCHEN,
    CB_ITEM_VIEW,       # новый callback
    CB_ITEM_TOGGLE,     # новый callback
    CB_CATEGORY,
    CB_BACK_CATEGORIES,
    CB_BACK_TO_CATEGORIES,
)

# Импорты админа (без изменений)
from .admin.handlers import admin_start, admin_callback, admin_text_input
from .admin.constant import (
    ADMIN_MAIN,
    ADMIN_SHIFTS,
    ADMIN_SELECT_EMPLOYEE,
    ADMIN_CALENDAR,
    ADMIN_DAY_PROGRESS,
    ADMIN_EDIT_ITEMS,
    ADMIN_EDIT_ITEM,
    ADMIN_DELETE_ITEM,
    ADMIN_AWAIT_ITEM_TYPE,
    ADMIN_AWAIT_ITEM_LOCATION,
    ADMIN_AWAIT_ITEM_CATEGORY,
    ADMIN_AWAIT_ITEM_DAY,
    ADMIN_AWAIT_ITEM_TEXT,
    ADMIN_AWAIT_EDIT_TEXT,
    CB_ADMIN_SHIFTS,
    CB_ADMIN_PROGRESS,
    CB_ADMIN_EDIT,
    CB_ADMIN_BACK,
    CB_ADMIN_EMPLOYEE,
    CB_ADMIN_EDIT_ITEM,
    CB_ADMIN_DELETE_ITEM,
    CB_ADMIN_CONFIRM_DELETE,
    CB_ADMIN_ADD_ITEM,
    CB_ADMIN_EDIT_ITEMS,
    CB_ADMIN_ITEM_TYPE,
    CB_ADMIN_ITEM_LOCATION,
    CB_ADMIN_ITEM_CATEGORY,
    CB_ADMIN_ITEM_DAY,
    CB_ADMIN_CANCEL,
    CB_ADMIN_MONTH_PREV,
    CB_ADMIN_MONTH_NEXT,
    CB_ADMIN_DAY,
    CB_ADMIN_BACK_TO_CALENDAR,
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
            # Состояния для сотрудников (обновлены)
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
                CallbackQueryHandler(view_item, pattern=f"^{CB_ITEM_VIEW}.*|^{CB_BACK_CATEGORIES}$|^{CB_BACK_MAIN}$"),
                CallbackQueryHandler(noop, pattern="^noop$")
            ],
            ITEM_DETAIL: [
                CallbackQueryHandler(toggle_item, pattern=f"^{CB_ITEM_TOGGLE}.*|^{CB_BACK_TO_CATEGORIES}$|^{CB_BACK_MAIN}$"),
            ],
            PROGRESS_VIEW: [
                CallbackQueryHandler(progress_back, pattern=f"^{CB_BACK_MAIN}$")
            ],

            # Состояния для админа (без изменений)
            ADMIN_MAIN: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_SHIFTS}$|^{CB_ADMIN_PROGRESS}$|^{CB_ADMIN_EDIT}$|^{CB_ADMIN_BACK}$")
            ],
            ADMIN_SHIFTS: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_BACK}$")
            ],
            ADMIN_SELECT_EMPLOYEE: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_EMPLOYEE}.*|^{CB_ADMIN_BACK}$")
            ],
            ADMIN_CALENDAR: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_MONTH_PREV}$|^{CB_ADMIN_MONTH_NEXT}$|^{CB_ADMIN_DAY}.*|^{CB_ADMIN_BACK}$|^{CB_ADMIN_BACK_TO_CALENDAR}$")
            ],
            ADMIN_DAY_PROGRESS: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_BACK_TO_CALENDAR}$|^{CB_ADMIN_BACK}$")
            ],
            ADMIN_EDIT_ITEMS: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_EDIT_ITEM}.*|^{CB_ADMIN_ADD_ITEM}$|^{CB_ADMIN_BACK}$|^{CB_ADMIN_EDIT_ITEMS}$")
            ],
            ADMIN_EDIT_ITEM: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_DELETE_ITEM}.*|^{CB_ADMIN_EDIT_ITEMS}$|^{CB_ADMIN_BACK}$")
            ],
            ADMIN_DELETE_ITEM: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_CONFIRM_DELETE}.*|^{CB_ADMIN_EDIT_ITEMS}$|^{CB_ADMIN_BACK}$")
            ],
            ADMIN_AWAIT_ITEM_TYPE: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_ITEM_TYPE}.*|^{CB_ADMIN_CANCEL}$|^{CB_ADMIN_BACK}$")
            ],
            ADMIN_AWAIT_ITEM_LOCATION: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_ITEM_LOCATION}.*|^{CB_ADMIN_BACK}$|^{CB_ADMIN_CANCEL}$")
            ],
            ADMIN_AWAIT_ITEM_CATEGORY: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_ITEM_CATEGORY}.*|^{CB_ADMIN_BACK}$|^{CB_ADMIN_CANCEL}$")
            ],
            ADMIN_AWAIT_ITEM_DAY: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_ITEM_DAY}.*|^{CB_ADMIN_BACK}$|^{CB_ADMIN_CANCEL}$")
            ],
            ADMIN_AWAIT_ITEM_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_input),
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_BACK}$|^{CB_ADMIN_CANCEL}$")
            ],
            ADMIN_AWAIT_EDIT_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_input),
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_BACK}$|^{CB_ADMIN_CANCEL}$")
            ],
        },
        fallbacks=[CommandHandler("start", start_router)],
        per_user=True,
        per_chat=False,
    )
    app.add_handler(conv_handler)