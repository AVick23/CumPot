from telegram.ext import CallbackQueryHandler, MessageHandler, filters
from .handlers import (
    edit_callback,
    edit_text_input,
)
from .constants import (
    ADMIN_EDIT_LOCATION, ADMIN_EDIT_CATEGORY, ADMIN_EDIT_ITEMS,
    ADMIN_ITEM_DETAIL, ADMIN_DELETE_CONFIRM, ADMIN_ADD_DAY,
    ADMIN_AWAIT_NEW_TEXT, ADMIN_AWAIT_EDIT_TEXT,
    ADMIN_AWAIT_ITEM_TYPE, ADMIN_AWAIT_DATE,
    ADMIN_AWAIT_HOUR, ADMIN_AWAIT_MINUTE,
    ADMIN_AWAIT_PHOTO_FLAG, ADMIN_AWAIT_NOTIFICATION_FLAG,
    ADMIN_EDIT_TOGGLE_PHOTO, ADMIN_EDIT_TOGGLE_NOTIFICATION, ADMIN_EDIT_CHANGE_TIME,
    CB_HOME, CB_TO_EDIT, CB_TO_CATEGORIES, CB_TO_ITEMS,
    CB_LOC_PREFIX, CB_CAT_PREFIX, CB_PAGE_PREFIX,
    CB_ITEM_PREFIX, CB_EDIT_ITEM_PREFIX, CB_DELETE_ITEM_PREFIX,
    CB_CONFIRM_DELETE_PREFIX, CB_ADD, CB_ADD_DAY_PREFIX,
    CB_CANCEL, CB_CANCEL_EDIT, CB_ADD_BACK_TEXT,
    CB_ITEM_TYPE_PREFIX, CB_DATE_PREFIX, CB_MONTH_PREV, CB_MONTH_NEXT,
    CB_HOUR_PREFIX, CB_MINUTE_PREFIX,
    CB_PHOTO_FLAG_PREFIX, CB_NOTIF_FLAG_PREFIX, CB_FLAGS_SKIP,
    CB_TOGGLE_PHOTO, CB_TOGGLE_NOTIFICATION, CB_CHANGE_TIME,
)


def register_editor_states(states: dict):
    states[ADMIN_EDIT_LOCATION] = [
        CallbackQueryHandler(edit_callback, pattern=f"^{CB_LOC_PREFIX}:.*|^{CB_HOME}$"),
    ]
    states[ADMIN_EDIT_CATEGORY] = [
        CallbackQueryHandler(edit_callback, pattern=f"^{CB_CAT_PREFIX}:.*|^{CB_TO_EDIT}$|^{CB_HOME}$"),
    ]
    states[ADMIN_EDIT_ITEMS] = [
        CallbackQueryHandler(edit_callback, pattern=f"^{CB_ITEM_PREFIX}:.*|^{CB_PAGE_PREFIX}:.*|^{CB_ADD}$|^{CB_TO_CATEGORIES}$|^{CB_HOME}$"),
    ]
    states[ADMIN_ITEM_DETAIL] = [
        CallbackQueryHandler(edit_callback, pattern=f"^{CB_EDIT_ITEM_PREFIX}:.*|^{CB_DELETE_ITEM_PREFIX}:.*|^{CB_TO_ITEMS}$|^{CB_TOGGLE_PHOTO}.*|^{CB_TOGGLE_NOTIFICATION}.*|^{CB_CHANGE_TIME}.*$"),
    ]
    states[ADMIN_DELETE_CONFIRM] = [
        CallbackQueryHandler(edit_callback, pattern=f"^{CB_CONFIRM_DELETE_PREFIX}:.*|^{CB_ITEM_PREFIX}:.*"),
    ]
    states[ADMIN_ADD_DAY] = [
        CallbackQueryHandler(edit_callback, pattern=f"^{CB_ADD_DAY_PREFIX}:.*|^{CB_TO_ITEMS}$|^{CB_CANCEL}$"),
    ]
    states[ADMIN_AWAIT_NEW_TEXT] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, edit_text_input),
        CallbackQueryHandler(edit_callback, pattern=f"^{CB_CANCEL}$|^{CB_HOME}$"),
    ]
    states[ADMIN_AWAIT_EDIT_TEXT] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, edit_text_input),
        CallbackQueryHandler(edit_callback, pattern=f"^{CB_CANCEL_EDIT}$|^{CB_HOME}$"),
    ]

    # Новые состояния для расширенного добавления
    states[ADMIN_AWAIT_ITEM_TYPE] = [
        CallbackQueryHandler(edit_callback, pattern=f"^{CB_ITEM_TYPE_PREFIX}.*|^{CB_CANCEL}$"),
    ]
    states[ADMIN_AWAIT_DATE] = [
        CallbackQueryHandler(edit_callback, pattern=f"^{CB_DATE_PREFIX}.*|^{CB_MONTH_PREV}$|^{CB_MONTH_NEXT}$|^{CB_CANCEL}$"),
    ]
    states[ADMIN_AWAIT_HOUR] = [
        CallbackQueryHandler(edit_callback, pattern=f"^{CB_HOUR_PREFIX}.*|^{CB_CANCEL}$"),
    ]
    states[ADMIN_AWAIT_MINUTE] = [
        CallbackQueryHandler(edit_callback, pattern=f"^{CB_MINUTE_PREFIX}.*|^{CB_CANCEL}$"),
    ]
    states[ADMIN_AWAIT_PHOTO_FLAG] = [
        CallbackQueryHandler(edit_callback, pattern=f"^{CB_PHOTO_FLAG_PREFIX}.*|^{CB_CANCEL}$"),
    ]
    states[ADMIN_AWAIT_NOTIFICATION_FLAG] = [
        CallbackQueryHandler(edit_callback, pattern=f"^{CB_NOTIF_FLAG_PREFIX}.*|^{CB_CANCEL}$"),
    ]