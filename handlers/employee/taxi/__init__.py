from telegram.ext import CallbackQueryHandler, MessageHandler, filters

from .handlers import (
    show_taxi_menu,
    taxi_callback,
    taxi_text_input,
    taxi_photo_input,
)

from .constants import (
    TAXI_MENU,
    TAXI_ADD_AMOUNT,
    TAXI_ADD_PHOTO,
    TAXI_HISTORY,
)


def register_taxi_states(states: dict):
    """Регистрирует состояния для работы с такси."""
    # Основное меню – только callback
    states[TAXI_MENU] = [
        CallbackQueryHandler(taxi_callback),
    ]

    # Ожидание ввода суммы – текст или callback
    states[TAXI_ADD_AMOUNT] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, taxi_text_input),
        CallbackQueryHandler(taxi_callback),
    ]

    # Ожидание фото – фото или callback
    states[TAXI_ADD_PHOTO] = [
        MessageHandler(filters.PHOTO, taxi_photo_input),
        CallbackQueryHandler(taxi_callback),
    ]

    # История – только callback
    states[TAXI_HISTORY] = [
        CallbackQueryHandler(taxi_callback),
    ]