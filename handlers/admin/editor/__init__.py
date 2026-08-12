from telegram.ext import CallbackQueryHandler, MessageHandler, filters

from .handlers import (
    edit_callback,
    edit_text_input,
)
from .constants import (
    ADMIN_EDIT_LOCATION,
    ADMIN_EDIT_CATEGORY,
    ADMIN_EDIT_ITEMS,
    ADMIN_ITEM_DETAIL,
    ADMIN_DELETE_CONFIRM,
    ADMIN_ADD_DAY,
    ADMIN_AWAIT_NEW_TEXT,
    ADMIN_AWAIT_EDIT_TEXT,
    ADMIN_AWAIT_ITEM_TYPE,
    ADMIN_AWAIT_DATE,
    ADMIN_AWAIT_HOUR,
    ADMIN_AWAIT_MINUTE,
    ADMIN_AWAIT_PHOTO_FLAG,
    ADMIN_AWAIT_NOTIFICATION_FLAG,
    ADMIN_AWAIT_DAYS,
    ADMIN_EDIT_TOGGLE_PHOTO,
    ADMIN_EDIT_TOGGLE_NOTIFICATION,
    ADMIN_EDIT_CHANGE_TIME,
    ADMIN_EDIT_CHANGE_DATE,
)


def register_editor_states(states: dict):
    """
    Регистрируем состояния редактора.

    Сделано сознательно просто:
    - в текстовых состояниях ждём текст + callback-кнопки
    - во всех остальных состояниях ждём только callback-кнопки

    Это избавляет от кучи хрупких regex-pattern'ов.
    """

    callback_only_states = [
        ADMIN_EDIT_LOCATION,
        ADMIN_EDIT_CATEGORY,
        ADMIN_EDIT_ITEMS,
        ADMIN_ITEM_DETAIL,
        ADMIN_DELETE_CONFIRM,
        ADMIN_ADD_DAY,
        ADMIN_AWAIT_ITEM_TYPE,
        ADMIN_AWAIT_DATE,
        ADMIN_AWAIT_HOUR,
        ADMIN_AWAIT_MINUTE,
        ADMIN_AWAIT_PHOTO_FLAG,
        ADMIN_AWAIT_NOTIFICATION_FLAG,
        ADMIN_AWAIT_DAYS,
        ADMIN_EDIT_TOGGLE_PHOTO,
        ADMIN_EDIT_TOGGLE_NOTIFICATION,
        ADMIN_EDIT_CHANGE_TIME,
        ADMIN_EDIT_CHANGE_DATE,
    ]

    text_states = [
        ADMIN_AWAIT_NEW_TEXT,
        ADMIN_AWAIT_EDIT_TEXT,
    ]

    for state in callback_only_states:
        states[state] = [
            CallbackQueryHandler(edit_callback),
        ]

    for state in text_states:
        states[state] = [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_text_input),
            CallbackQueryHandler(edit_callback),
        ]