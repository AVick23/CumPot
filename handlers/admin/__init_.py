from telegram.ext import Application, ConversationHandler, CommandHandler, CallbackQueryHandler
from .handlers import admin_start, admin_callback, employee_selection, edit_items_callback
from .constant import *

def register_handlers(app: Application):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", admin_start)],
        states={
            ADMIN_MAIN: [
                CallbackQueryHandler(admin_callback, pattern="|".join([CB_ADMIN_SHIFTS, CB_ADMIN_PROGRESS, CB_ADMIN_EDIT, CB_ADMIN_BACK]))
            ],
            ADMIN_SHIFTS: [
                CallbackQueryHandler(admin_callback, pattern=CB_ADMIN_BACK)
            ],
            ADMIN_SELECT_EMPLOYEE: [
                CallbackQueryHandler(employee_selection, pattern=f"^{CB_ADMIN_EMPLOYEE}.*|^{CB_ADMIN_BACK}$"),
            ],
            ADMIN_SHOW_PROGRESS: [
                CallbackQueryHandler(employee_selection, pattern=CB_ADMIN_BACK),
            ],
            ADMIN_EDIT_ITEMS: [
                CallbackQueryHandler(edit_items_callback, pattern=f"^{CB_ADMIN_EDIT_ITEM}.*|^{CB_ADMIN_ADD_ITEM}$|^{CB_ADMIN_BACK}$|^{CB_ADMIN_EDIT_ITEMS}$"),
            ],
            ADMIN_EDIT_ITEM: [
                CallbackQueryHandler(edit_items_callback, pattern=f"^{CB_ADMIN_DELETE_ITEM}.*|^{CB_ADMIN_EDIT_ITEMS}$|^{CB_ADMIN_BACK}$"),
            ],
            ADMIN_DELETE_ITEM: [
                CallbackQueryHandler(edit_items_callback, pattern=f"^{CB_ADMIN_CONFIRM_DELETE}.*|^{CB_ADMIN_EDIT_ITEMS}$|^{CB_ADMIN_BACK}$"),
            ],
        },
        fallbacks=[CommandHandler("start", admin_start)],
        per_user=True,
        per_chat=False,
    )
    app.add_handler(conv_handler)