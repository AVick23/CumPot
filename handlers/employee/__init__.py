from telegram.ext import Application, ConversationHandler, CommandHandler, CallbackQueryHandler
# Экспортируем всё необходимое для главного __init__
from .handlers import (
    start_menu,
    main_menu_callback,
    location_selection,
    checklist_action,
    progress_back,
    noop
)
from .constant import *

def register_handlers(app: Application):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_menu)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(main_menu_callback, pattern="|".join([CB_SHIFT_MARK, CB_CHECKLIST, CB_PROGRESS, CB_BACK_MAIN]))
            ],
            SELECT_LOCATION: [
                CallbackQueryHandler(location_selection, pattern="|".join([CB_SHIFT_BAR, CB_SHIFT_KITCHEN, CB_BACK_MAIN]))
            ],
            CHECKLIST_VIEW: [
                CallbackQueryHandler(checklist_action, pattern="|".join([CB_ITEM_DONE, CB_ITEM_UNDO, CB_BACK_MAIN])),
            ],
            PROGRESS_VIEW: [
                CallbackQueryHandler(progress_back, pattern=CB_BACK_MAIN),
            ],
        },
        fallbacks=[CommandHandler("start", start_menu)],
        per_user=True,
        per_chat=False,
    )
    app.add_handler(conv_handler)