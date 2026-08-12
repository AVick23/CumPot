from telegram.ext import CallbackQueryHandler
from .handlers import show_calendar, show_day_report, calendar_callback
from .constants import ADMIN_CALENDAR, ADMIN_DAY_REPORT, CB_HOME, CB_TO_CALENDAR, CB_PREV_MONTH, CB_NEXT_MONTH, CB_DAY_PREFIX


def register_report_states(states: dict):
    states[ADMIN_CALENDAR] = [
        CallbackQueryHandler(calendar_callback, pattern=f"^{CB_PREV_MONTH}$|^{CB_NEXT_MONTH}$|^{CB_DAY_PREFIX}:.*|^{CB_HOME}$"),
    ]
    states[ADMIN_DAY_REPORT] = [
        CallbackQueryHandler(calendar_callback, pattern=f"^{CB_TO_CALENDAR}$|^{CB_HOME}$|^show_media:.*$"),
    ]