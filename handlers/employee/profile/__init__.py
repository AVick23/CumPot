from telegram.ext import CallbackQueryHandler, MessageHandler, filters

from .handlers import (
    show_profile,
    profile_callback,
    profile_text_input,
)

from .constants import (
    PROFILE_VIEW,
    PROFILE_EDIT_NAME,
    PROFILE_EDIT_PHONE,
    PROFILE_EDIT_BIRTHDAY,
    PROFILE_EDIT_ADDRESS,
    PROFILE_EDIT_RESPONSIBILITIES,
    PROFILE_EDIT_POSITION,
)


def register_profile_states(states: dict):
    """Регистрирует состояния для работы с профилем."""
    # Состояние просмотра – только callback'и
    states[PROFILE_VIEW] = [
        CallbackQueryHandler(profile_callback),
    ]

    # Состояния редактирования – ожидают текст + callback для отмены
    edit_states = [
        PROFILE_EDIT_NAME,
        PROFILE_EDIT_PHONE,
        PROFILE_EDIT_BIRTHDAY,
        PROFILE_EDIT_ADDRESS,
        PROFILE_EDIT_RESPONSIBILITIES,
        PROFILE_EDIT_POSITION,
    ]
    for state in edit_states:
        states[state] = [
            MessageHandler(filters.TEXT & ~filters.COMMAND, profile_text_input),
            CallbackQueryHandler(profile_callback),
        ]