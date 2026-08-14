from telegram.ext import CallbackQueryHandler

from .handlers import calendar_callback
from .constants import (
    ADMIN_CALENDAR,
    ADMIN_DAY_REPORT,
    ADMIN_PHOTO_OVERVIEW,
    ADMIN_PHOTO_LOCATION,
    ADMIN_PHOTO_CATEGORY,
    ADMIN_TAXI_PHOTO_OVERVIEW,
    ADMIN_TAXI_PHOTO_USER,
)


def register_report_states(states: dict):
    """
    Регистрируем состояния админ-отчётов.
    Один CallbackQueryHandler на состояние, чтобы не плодить
    хрупкие regex-паттерны и нормально поддерживать новый фотоотчёт.
    """

    states[ADMIN_CALENDAR] = [
        CallbackQueryHandler(calendar_callback),
    ]

    states[ADMIN_DAY_REPORT] = [
        CallbackQueryHandler(calendar_callback),
    ]

    states[ADMIN_PHOTO_OVERVIEW] = [
        CallbackQueryHandler(calendar_callback),
    ]

    states[ADMIN_PHOTO_LOCATION] = [
        CallbackQueryHandler(calendar_callback),
    ]

    states[ADMIN_PHOTO_CATEGORY] = [
        CallbackQueryHandler(calendar_callback),
    ]

    states[ADMIN_TAXI_PHOTO_OVERVIEW] = [
        CallbackQueryHandler(calendar_callback),
    ]

    states[ADMIN_TAXI_PHOTO_USER] = [
        CallbackQueryHandler(calendar_callback),
    ]