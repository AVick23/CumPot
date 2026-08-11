from telegram.ext import (
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from .handlers import (
    employee_start,
    onboarding_name_input,
    onboarding_position,
    main_menu_callback,
    category_selection,
    view_item,
    toggle_item_callback,
    progress_back,
    noop as employee_noop,
)

from .constants import (
    ONBOARD_NAME,
    ONBOARD_POSITION,
    MAIN_MENU,
    CATEGORY_SELECT,
    CHECKLIST_VIEW,
    ITEM_DETAIL,
    PROGRESS_VIEW,
    CB_START_SHIFT,
    CB_CHECKLIST,
    CB_PROGRESS,
    CB_POSITION_PREFIX,
    CB_CATEGORY_PREFIX,
    CB_ITEM_PREFIX,
    CB_TOGGLE_PREFIX,
    CB_BACK_MENU,
    CB_BACK_CATEGORIES,
)


def get_employee_entry_point():
    """Возвращает точку входа для сотрудника"""
    return employee_start


def register_employee_states(states: dict):
    """
    Регистрирует все состояния сотрудника в переданный словарь states.
    Корневой роутер не знает о деталях реализации employee.
    """

    def emp_state(handler, pattern: str):
        return [
            CallbackQueryHandler(handler, pattern=pattern),
            CallbackQueryHandler(employee_noop, pattern="^noop$"),
        ]

    # Онбординг
    states[ONBOARD_NAME] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_name_input),
    ]

    states[ONBOARD_POSITION] = emp_state(
        onboarding_position,
        f"^{CB_POSITION_PREFIX}.*"
    )

    # Главное меню (БЕЗ CB_END_SHIFT)
    states[MAIN_MENU] = emp_state(
        main_menu_callback,
        f"^{CB_START_SHIFT}$|^{CB_CHECKLIST}$|^{CB_PROGRESS}$|^{CB_BACK_MENU}$"
    )

    # Чек-листы
    states[CATEGORY_SELECT] = emp_state(
        category_selection,
        f"^{CB_CATEGORY_PREFIX}.*|^{CB_BACK_MENU}$"
    )

    states[CHECKLIST_VIEW] = emp_state(
        view_item,
        f"^{CB_ITEM_PREFIX}.*|^{CB_BACK_CATEGORIES}$|^{CB_BACK_MENU}$"
    )

    states[ITEM_DETAIL] = emp_state(
        toggle_item_callback,
        f"^{CB_TOGGLE_PREFIX}.*|^{CB_BACK_CATEGORIES}$|^{CB_BACK_MENU}$"
    )

    # Прогресс
    states[PROGRESS_VIEW] = emp_state(
        progress_back,
        f"^{CB_BACK_MENU}$"
    )