from telegram.ext import Application, ConversationHandler, CommandHandler, CallbackQueryHandler
from .handlers import (
    start_menu,
    main_menu_callback,
    location_selection,
    category_selection,          # обязательно импортируйте
    checklist_action,
    progress_back,
    noop
)
from .constants import *

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
            CATEGORY_SELECT: [   # ДОБАВЬТЕ ЭТОТ БЛОК
                CallbackQueryHandler(category_selection, pattern=f"^{CB_CATEGORY}.*|^{CB_BACK_MAIN}$"),
            ],
            CHECKLIST_VIEW: [
                CallbackQueryHandler(checklist_action, pattern=f"^{CB_ITEM_DONE}.*|^{CB_ITEM_UNDO}.*|^{CB_BACK_CATEGORIES}$|^{CB_BACK_MAIN}$"),
                CallbackQueryHandler(noop, pattern="^noop$"),
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