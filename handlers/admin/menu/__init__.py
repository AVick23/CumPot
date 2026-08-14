from telegram.ext import CallbackQueryHandler
from .handlers import main_menu_callback, show_main, show_shifts
from .constants import ADMIN_MAIN, ADMIN_SHIFTS, CB_HOME, CB_SHIFTS, CB_CALENDAR, CB_EDIT, CB_EMPLOYEES


def register_menu_states(states: dict):
    states[ADMIN_MAIN] = [
        CallbackQueryHandler(main_menu_callback, pattern=f"^{CB_SHIFTS}$|^{CB_CALENDAR}$|^{CB_EDIT}$|^{CB_HOME}$|^{CB_EMPLOYEES}$"),
    ]
    states[ADMIN_SHIFTS] = [
        CallbackQueryHandler(main_menu_callback, pattern=f"^{CB_HOME}$"),
    ]