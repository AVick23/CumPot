from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes
from db.users import save_user, get_user
from config import ADMIN_IDS

from .employee.handlers import (
    start_menu, main_menu_callback, location_selection, category_selection,
    view_item, toggle_item, back_to_list, progress_back, noop,
)
from .employee.constants import (
    MAIN_MENU, SELECT_LOCATION, CHECKLIST_VIEW, PROGRESS_VIEW,
    CATEGORY_SELECT, ITEM_DETAIL, CB_BACK_MAIN, CB_SHIFT_MARK,
    CB_CHECKLIST, CB_PROGRESS, CB_SHIFT_BAR, CB_SHIFT_KITCHEN,
    CB_ITEM_VIEW, CB_ITEM_TOGGLE, CB_CATEGORY, CB_BACK_CATEGORIES,
    CB_BACK_TO_CATEGORIES,
)

from .admin.handlers import admin_start, admin_callback, admin_text_input
from .admin.constants import (
    ADMIN_MAIN, ADMIN_SHIFTS, ADMIN_EMPLOYEES, ADMIN_CALENDAR,
    ADMIN_DAY_PROGRESS, ADMIN_EDIT_LOCATION, ADMIN_EDIT_CATEGORY,
    ADMIN_EDIT_ITEMS, ADMIN_ITEM_DETAIL, ADMIN_DELETE_CONFIRM,
    ADMIN_ADD_DAY, ADMIN_AWAIT_NEW_TEXT, ADMIN_AWAIT_EDIT_TEXT,
    CB_HOME, CB_SHIFTS, CB_EMPLOYEES, CB_EDIT, CB_EMP_PREFIX,
    CB_PREV_MONTH, CB_NEXT_MONTH, CB_DAY_PREFIX, CB_TO_EMPLOYEES,
    CB_TO_CALENDAR, CB_TO_EDIT, CB_TO_CATEGORIES, CB_TO_ITEMS,
    CB_LOC_PREFIX, CB_CAT_PREFIX, CB_PAGE_PREFIX, CB_ITEM_PREFIX,
    CB_EDIT_ITEM_PREFIX, CB_DELETE_ITEM_PREFIX, CB_CONFIRM_DELETE_PREFIX,
    CB_ADD, CB_ADD_DAY_PREFIX, CB_ADD_BACK_TEXT, CB_CANCEL, CB_CANCEL_EDIT,
)


async def start_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return ConversationHandler.END
    save_user(user.id, user.username, user.first_name, user.last_name)
    user_data = get_user(user.id)
    if user_data and user_data.get('is_admin'):
        return await admin_start(update, context)
    else:
        return await start_menu(update, context)


def register_handlers(app: Application):
    admin_text_cb_pattern = f"^(?:{CB_CANCEL}|{CB_CANCEL_EDIT}|{CB_ADD_BACK_TEXT}|{CB_HOME})$"

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_router)],
        states={
            # EMPLOYEE
            MAIN_MENU: [CallbackQueryHandler(main_menu_callback, pattern=f"^{CB_SHIFT_MARK}$|^{CB_CHECKLIST}$|^{CB_PROGRESS}$|^{CB_BACK_MAIN}$")],
            SELECT_LOCATION: [CallbackQueryHandler(location_selection, pattern=f"^{CB_SHIFT_BAR}$|^{CB_SHIFT_KITCHEN}$|^{CB_BACK_MAIN}$")],
            CATEGORY_SELECT: [CallbackQueryHandler(category_selection, pattern=f"^{CB_CATEGORY}.*|^{CB_BACK_MAIN}$")],
            CHECKLIST_VIEW: [
                CallbackQueryHandler(view_item, pattern=f"^{CB_ITEM_VIEW}.*|^{CB_BACK_CATEGORIES}$|^{CB_BACK_MAIN}$"),
                CallbackQueryHandler(noop, pattern="^noop$"),
            ],
            ITEM_DETAIL: [
                CallbackQueryHandler(toggle_item, pattern=f"^{CB_ITEM_TOGGLE}.*|^{CB_BACK_MAIN}$"),
                CallbackQueryHandler(back_to_list, pattern=f"^{CB_BACK_TO_CATEGORIES}$"),
            ],
            PROGRESS_VIEW: [CallbackQueryHandler(progress_back, pattern=f"^{CB_BACK_MAIN}$")],
            # ADMIN
            ADMIN_MAIN: [CallbackQueryHandler(admin_callback, pattern=f"^{CB_SHIFTS}$|^{CB_EMPLOYEES}$|^{CB_EDIT}$|^{CB_HOME}$")],
            ADMIN_SHIFTS: [CallbackQueryHandler(admin_callback, pattern=f"^{CB_HOME}$")],
            ADMIN_EMPLOYEES: [CallbackQueryHandler(admin_callback, pattern=f"^{CB_EMP_PREFIX}.*|^{CB_HOME}$")],
            ADMIN_CALENDAR: [CallbackQueryHandler(admin_callback, pattern=f"^{CB_PREV_MONTH}$|^{CB_NEXT_MONTH}$|^{CB_DAY_PREFIX}.*|^{CB_TO_EMPLOYEES}$|^{CB_HOME}$")],
            ADMIN_DAY_PROGRESS: [CallbackQueryHandler(admin_callback, pattern=f"^{CB_TO_CALENDAR}$|^{CB_TO_EMPLOYEES}$|^{CB_HOME}$")],
            ADMIN_EDIT_LOCATION: [CallbackQueryHandler(admin_callback, pattern=f"^{CB_LOC_PREFIX}.*|^{CB_HOME}$")],
            ADMIN_EDIT_CATEGORY: [CallbackQueryHandler(admin_callback, pattern=f"^{CB_CAT_PREFIX}.*|^{CB_TO_EDIT}$|^{CB_HOME}$")],
            ADMIN_EDIT_ITEMS: [CallbackQueryHandler(admin_callback, pattern=f"^{CB_ITEM_PREFIX}.*|^{CB_PAGE_PREFIX}.*|^{CB_ADD}$|^{CB_TO_CATEGORIES}$|^{CB_HOME}$")],
            ADMIN_ITEM_DETAIL: [CallbackQueryHandler(admin_callback, pattern=f"^{CB_EDIT_ITEM_PREFIX}.*|^{CB_DELETE_ITEM_PREFIX}.*|^{CB_TO_ITEMS}$")],
            ADMIN_DELETE_CONFIRM: [CallbackQueryHandler(admin_callback, pattern=f"^{CB_CONFIRM_DELETE_PREFIX}.*|^{CB_ITEM_PREFIX}.*")],
            ADMIN_ADD_DAY: [CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADD_DAY_PREFIX}.*|^{CB_TO_ITEMS}$|^{CB_CANCEL}$")],
            ADMIN_AWAIT_NEW_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_input),
                CallbackQueryHandler(admin_callback, pattern=admin_text_cb_pattern),
            ],
            ADMIN_AWAIT_EDIT_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_input),
                CallbackQueryHandler(admin_callback, pattern=admin_text_cb_pattern),
            ],
        },
        fallbacks=[CommandHandler("start", start_router)],
        per_user=True, per_chat=False,
    )
    app.add_handler(conv_handler)