from telegram.ext import Application, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from .handlers import admin_start, admin_callback, admin_text_input
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
            ADMIN_EMPLOYEE_LIST: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_EMPLOYEE}.*|^{CB_ADMIN_BACK}$")
            ],
            ADMIN_CALENDAR: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_MONTH_PREV}$|^{CB_ADMIN_MONTH_NEXT}$|^{CB_ADMIN_DAY}.*|^{CB_ADMIN_BACK}$|^{CB_ADMIN_BACK_TO_CALENDAR}$")
            ],
            ADMIN_DAY_PROGRESS: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_BACK_TO_CALENDAR}$|^{CB_ADMIN_BACK}$")
            ],
            ADMIN_EDIT_CATEGORIES: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_EDIT_CATEGORY}.*|^{CB_ADMIN_ADD_ITEM}$|^{CB_ADMIN_BACK}$")
            ],
            ADMIN_EDIT_ITEMS_LIST: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_EDIT_ITEM}.*|^{CB_ADMIN_EDIT_DELETE}.*|^{CB_ADMIN_EDIT_BACK}$|^{CB_ADMIN_BACK}$")
            ],
            ADMIN_DELETE_CONFIRM: [
                CallbackQueryHandler(admin_callback, pattern=f"^{CB_ADMIN_EDIT_CONFIRM_DELETE}.*|^{CB_ADMIN_EDIT_BACK}$|^{CB_ADMIN_BACK}$")
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
        fallbacks=[CommandHandler("start", admin_start)],
        per_user=True,
        per_chat=False,
    )
    app.add_handler(conv_handler)