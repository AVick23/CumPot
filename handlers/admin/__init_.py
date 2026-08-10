from telegram.ext import Application, ConversationHandler, CommandHandler, CallbackQueryHandler
# Экспортируем всё необходимое для главного __init__
from .handlers import admin_start, admin_callback
from .constant import *

def register_handlers(app: Application):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", admin_start)],
        states={
            ADMIN_MAIN: [
                CallbackQueryHandler(admin_callback, pattern="|".join([CB_ADMIN_SHIFTS, CB_ADMIN_PROGRESS, CB_ADMIN_EDIT]))
            ],
            ADMIN_SHIFTS: [
                CallbackQueryHandler(admin_callback, pattern=CB_ADMIN_BACK)
            ],
            ADMIN_PROGRESS: [
                CallbackQueryHandler(admin_callback, pattern=CB_ADMIN_BACK)
            ],
            ADMIN_EDIT: [
                CallbackQueryHandler(admin_callback, pattern=CB_ADMIN_BACK)
            ],
        },
        fallbacks=[CommandHandler("start", admin_start)],
        per_user=True,
        per_chat=False,
    )
    app.add_handler(conv_handler)