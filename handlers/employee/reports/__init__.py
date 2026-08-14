from telegram.ext import CallbackQueryHandler, MessageHandler, filters
from .handlers import (
    show_reports_menu,
    report_callback,
    receive_report_text,
)
from .constants import (
    REPORT_SELECT_TYPE,
    REPORT_VIEW_DATE,
    REPORT_VIEW_DETAIL,
    REPORT_AWAIT_TEXT,
)


def register_report_states(states: dict):
    states[REPORT_SELECT_TYPE] = [
        CallbackQueryHandler(report_callback),
    ]
    states[REPORT_VIEW_DATE] = [
        CallbackQueryHandler(report_callback),
    ]
    states[REPORT_VIEW_DETAIL] = [
        CallbackQueryHandler(report_callback),
    ]
    states[REPORT_AWAIT_TEXT] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_report_text),
        CallbackQueryHandler(report_callback),
    ]