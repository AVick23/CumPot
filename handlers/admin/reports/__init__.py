from telegram.ext import CallbackQueryHandler, MessageHandler, filters

from .handlers import (
    show_reports_menu,
    report_callback,
    receive_report_text,
)

from .constants import (
    REPORT_HOME,
    REPORT_EDITOR,
    REPORT_TEXT_MODE,
    REPORT_SECTION_MENU,
    REPORT_SECTION_LIST,
    REPORT_AWAIT_SECTION,
    REPORT_CALENDAR,
)


def register_report_states(states: dict):
    states[REPORT_HOME] = [
        CallbackQueryHandler(report_callback),
    ]

    states[REPORT_EDITOR] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_report_text),
        CallbackQueryHandler(report_callback),
    ]

    states[REPORT_TEXT_MODE] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_report_text),
        CallbackQueryHandler(report_callback),
    ]

    states[REPORT_SECTION_MENU] = [
        CallbackQueryHandler(report_callback),
    ]

    states[REPORT_SECTION_LIST] = [
        CallbackQueryHandler(report_callback),
    ]

    states[REPORT_AWAIT_SECTION] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_report_text),
        CallbackQueryHandler(report_callback),
    ]

    states[REPORT_CALENDAR] = [
        CallbackQueryHandler(report_callback),
    ]