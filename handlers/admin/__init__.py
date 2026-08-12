from telegram.ext import (
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from .handlers import admin_start, admin_callback, admin_text_input
from .constants import (
    ADMIN_MAIN, ADMIN_SHIFTS, ADMIN_CALENDAR, ADMIN_DAY_REPORT,
    ADMIN_EDIT_LOCATION, ADMIN_EDIT_CATEGORY, ADMIN_EDIT_ITEMS,
    ADMIN_ITEM_DETAIL, ADMIN_DELETE_CONFIRM,
    ADMIN_ADD_DAY, ADMIN_AWAIT_NEW_TEXT, ADMIN_AWAIT_EDIT_TEXT,
    CB_CANCEL, CB_CANCEL_EDIT, CB_ADD_BACK_TEXT, CB_HOME,
)


def get_admin_entry_point():
    return admin_start


def register_admin_states(states: dict):
    text_cb_pattern = f"^(?:{CB_CANCEL}|{CB_CANCEL_EDIT}|{CB_ADD_BACK_TEXT}|{CB_HOME}|noop)$"

    def admin_state(pattern: str):
        return [
            CallbackQueryHandler(admin_callback, pattern=pattern),
            CallbackQueryHandler(admin_callback, pattern="^noop$"),
        ]

    # Импортируем остальные константы, используемые в состояниях
    from .constants import (
        CB_SHIFTS, CB_CALENDAR, CB_EDIT,
        CB_PREV_MONTH, CB_NEXT_MONTH, CB_DAY_PREFIX,
        CB_TO_CALENDAR, CB_TO_EDIT, CB_TO_CATEGORIES, CB_TO_ITEMS,
        CB_LOC_PREFIX, CB_CAT_PREFIX, CB_PAGE_PREFIX,
        CB_ITEM_PREFIX as CB_ADMIN_ITEM_PREFIX,
        CB_EDIT_ITEM_PREFIX, CB_DELETE_ITEM_PREFIX, CB_CONFIRM_DELETE_PREFIX,
        CB_ADD, CB_ADD_DAY_PREFIX,
    )

    states[ADMIN_MAIN] = admin_state(f"^{CB_SHIFTS}$|^{CB_CALENDAR}$|^{CB_EDIT}$|^{CB_HOME}$")
    states[ADMIN_SHIFTS] = admin_state(f"^{CB_HOME}$")
    states[ADMIN_CALENDAR] = admin_state(
        f"^{CB_PREV_MONTH}$|^{CB_NEXT_MONTH}$|^{CB_DAY_PREFIX}.*|^{CB_HOME}$"
    )
    states[ADMIN_DAY_REPORT] = admin_state(f"^{CB_TO_CALENDAR}$|^{CB_HOME}$")
    states[ADMIN_EDIT_LOCATION] = admin_state(f"^{CB_LOC_PREFIX}.*|^{CB_HOME}$")
    states[ADMIN_EDIT_CATEGORY] = admin_state(f"^{CB_CAT_PREFIX}.*|^{CB_TO_EDIT}$|^{CB_HOME}$")
    states[ADMIN_EDIT_ITEMS] = admin_state(
        f"^{CB_ADMIN_ITEM_PREFIX}.*|^{CB_PAGE_PREFIX}.*|^{CB_ADD}$|^{CB_TO_CATEGORIES}$|^{CB_HOME}$"
    )
    states[ADMIN_ITEM_DETAIL] = admin_state(
        f"^{CB_EDIT_ITEM_PREFIX}.*|^{CB_DELETE_ITEM_PREFIX}.*|^{CB_TO_ITEMS}$"
    )
    states[ADMIN_DELETE_CONFIRM] = admin_state(
        f"^{CB_CONFIRM_DELETE_PREFIX}.*|^{CB_ADMIN_ITEM_PREFIX}.*"
    )
    states[ADMIN_ADD_DAY] = admin_state(
        f"^{CB_ADD_DAY_PREFIX}.*|^{CB_TO_ITEMS}$|^{CB_CANCEL}$"
    )
    states[ADMIN_AWAIT_NEW_TEXT] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_input),
        CallbackQueryHandler(admin_callback, pattern=text_cb_pattern),
    ]
    states[ADMIN_AWAIT_EDIT_TEXT] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_input),
        CallbackQueryHandler(admin_callback, pattern=text_cb_pattern),
    ]