from telegram.ext import (
    Application,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from config import ADMIN_IDS

from .constants import (
    ADMIN_MAIN,
    ADMIN_SHIFTS,
    ADMIN_EMPLOYEES,
    ADMIN_CALENDAR,
    ADMIN_DAY_PROGRESS,
    ADMIN_EDIT_LOCATION,
    ADMIN_EDIT_CATEGORY,
    ADMIN_EDIT_ITEMS,
    ADMIN_ITEM_DETAIL,
    ADMIN_DELETE_CONFIRM,
    ADMIN_ADD_DAY,
    ADMIN_AWAIT_NEW_TEXT,
    ADMIN_AWAIT_EDIT_TEXT,
    CB_CANCEL,
    CB_CANCEL_EDIT,
    CB_ADD_BACK_TEXT,
    CB_HOME,
)

from .handlers import (
    admin_start,
    admin_callback,
    admin_text_input,
)


TEXT_CALLBACK_PATTERN = f"^(?:{CB_CANCEL}|{CB_CANCEL_EDIT}|{CB_ADD_BACK_TEXT}|{CB_HOME})$"


def register_admin(app: Application) -> None:
    non_text_states = [
        ADMIN_MAIN,
        ADMIN_SHIFTS,
        ADMIN_EMPLOYEES,
        ADMIN_CALENDAR,
        ADMIN_DAY_PROGRESS,
        ADMIN_EDIT_LOCATION,
        ADMIN_EDIT_CATEGORY,
        ADMIN_EDIT_ITEMS,
        ADMIN_ITEM_DETAIL,
        ADMIN_DELETE_CONFIRM,
        ADMIN_ADD_DAY,
    ]

    states = {
        state: [CallbackQueryHandler(admin_callback)]
        for state in non_text_states
    }

    states[ADMIN_AWAIT_NEW_TEXT] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_input),
        CallbackQueryHandler(admin_callback, pattern=TEXT_CALLBACK_PATTERN),
    ]

    states[ADMIN_AWAIT_EDIT_TEXT] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_input),
        CallbackQueryHandler(admin_callback, pattern=TEXT_CALLBACK_PATTERN),
    ]

    admin_filter = filters.User(user_id=ADMIN_IDS) if ADMIN_IDS else filters.User(user_id=set())

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", admin_start, filters=admin_filter)],
        states=states,
        fallbacks=[CommandHandler("start", admin_start, filters=admin_filter)],
        per_user=True,
        per_chat=False,
        allow_reentry=True,
    )

    # Важно: добавляем админа первым, чтобы /start админа не перехватил employee-хендлер
    app.add_handler(conv_handler, group=0)