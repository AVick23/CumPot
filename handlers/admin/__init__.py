from .menu import register_menu_states
from .reports import register_report_states
from .editor import register_editor_states
from .menu.handlers import show_main


def get_admin_entry_point():
    """Возвращает точку входа для админа (главное меню)"""
    return show_main


def register_admin_states(states: dict):
    """Регистрирует все состояния админа из подпакетов"""
    register_menu_states(states)
    register_report_states(states)
    register_editor_states(states)