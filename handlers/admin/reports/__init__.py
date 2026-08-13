from telegram.ext import CallbackQueryHandler

from .handlers import calendar_callback
from .constants import (
    ADMIN_CALENDAR,
    ADMIN_DAY_REPORT,
)


def register_report_states(states: dict):
    """
    Регистрируем состояния отчётов.

    Используется один CallbackQueryHandler на состояние,
    чтобы не зависеть от хрупких regex-паттернов.
    """
    states[ADMIN_CALENDAR] = [
        CallbackQueryHandler(calendar_callback),
    ]

    states[ADMIN_DAY_REPORT] = [
        CallbackQueryHandler(calendar_callback),
    ]