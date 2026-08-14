from telegram.ext import CallbackQueryHandler, MessageHandler, filters

from .handlers import (
    show_reports_menu,
    report_callback,
    receive_report_text,
)

from .constants import (
    REPORT_HOME,
    REPORT_HISTORY,
    REPORT_EDITOR,
    REPORT_AWAIT_TEXT,
    REPORT_AWAIT_SECTION,
)


def register_report_states(states: dict):
    # Главный экран
    states[REPORT_HOME] = [
        CallbackQueryHandler(report_callback),
    ]

    # История
    states[REPORT_HISTORY] = [
        CallbackQueryHandler(report_callback),
    ]

    # Редактор черновика
    states[REPORT_EDITOR] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_report_text),
        CallbackQueryHandler(report_callback),
    ]

    # Ожидание полного текста
    states[REPORT_AWAIT_TEXT] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_report_text),
        CallbackQueryHandler(report_callback),
    ]

    # Ожидание значения конкретного раздела
    states[REPORT_AWAIT_SECTION] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_report_text),
        CallbackQueryHandler(report_callback),
    ]