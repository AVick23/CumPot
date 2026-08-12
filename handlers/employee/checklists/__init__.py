# Экспортируем всё для регистрации в employee/__init__.py
from .handlers import (
    show_categories,
    category_selection,
    show_checklist,
    show_current_checklist,
    show_item_detail,
    view_item,
    toggle_item_callback,
    show_photo_prompt,
    photo_input,
    photo_wrong_type,
    photo_cancel,
    photo_state_guard,
    show_progress,
    progress_back,
    noop,
)
from .keyboards import (
    categories_keyboard,
    checklist_keyboard,
    item_detail_keyboard,
    progress_keyboard,
    photo_prompt_keyboard,
)
from .utils import build_photo_caption, item_detail_text
from .constants import *


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
        CallbackQueryHandler(edit_callback, pattern=f"^{CB_EDIT_ITEM_PREFIX}:.*|^{CB_DELETE_ITEM_PREFIX}:.*|^{CB_TO_ITEMS}$|^{CB_TOGGLE_PHOTO}.*|^{CB_TOGGLE_NOTIFICATION}.*|^{CB_CHANGE_TIME}.*|^{CB_ADD_DAY_PREFIX}.*$"),
    ]
    states[ADMIN_DELETE_CONFIRM] = [
        CallbackQueryHandler(edit_callback, pattern=f"^{CB_CONFIRM_DELETE_PREFIX}:.*|^{CB_ITEM_PREFIX}:.*"),
    ]
    states[ADMIN_ADD_DAY] = [
        CallbackQueryHandler(edit_callback, pattern=f"^{CB_ADD_DAY_PREFIX}:.*|^{CB_TO_ITEMS}$|^{CB_CANCEL}$"),
    ]
    states[ADMIN_AWAIT_NEW_TEXT] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, edit_text_input),
        CallbackQueryHandler(edit_callback, pattern=f"^{CB_CANCEL}$|^{CB_HOME}$|^{CB_ADD_BACK_TEXT}$"),
    ]
    states[ADMIN_AWAIT_EDIT_TEXT] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, edit_text_input),
        CallbackQueryHandler(edit_callback, pattern=f"^{CB_CANCEL_EDIT}$|^{CB_HOME}$"),
    ]
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
    states[ADMIN_AWAIT_DAYS] = [
        CallbackQueryHandler(edit_callback, pattern=f"^{CB_DAY_TOGGLE_PREFIX}.*|^{CB_DAYS_CONFIRM}$|^{CB_DAYS_CANCEL}$|^{CB_CANCEL}$"),
    ]