from telegram.ext import CallbackQueryHandler, MessageHandler, filters

from .menu.handlers import employee_start
from .menu import register_menu_states
from .checklists.handlers import (
    category_selection,
    view_item,
    toggle_item_callback,
    photo_input,
    photo_wrong_type,
    photo_cancel,
    photo_state_guard,
    progress_back,
    noop,
)

from .menu.constants import (
    ONBOARD_NAME,
    ONBOARD_POSITION,
    MAIN_MENU,
    SELECT_SHIFT_TYPE,
    CB_START_SHIFT,
    CB_CHECKLIST,
    CB_PROGRESS,
    CB_POSITION_PREFIX,
    CB_BACK_MENU,
)

from .checklists.constants import (
    CATEGORY_SELECT,
    CHECKLIST_VIEW,
    ITEM_DETAIL,
    PROGRESS_VIEW,
    AWAIT_TASK_PHOTO,
    CB_CATEGORY_PREFIX,
    CB_ITEM_PREFIX,
    CB_TOGGLE_PREFIX,
    CB_PHOTO_PREFIX,
    CB_VIEW_PHOTO_PREFIX,
    CB_PHOTO_CANCEL,
    CB_BACK_CATEGORIES,
)

from .menu.handlers import (
    onboarding_name_input,
    onboarding_wrong_type_name,
    onboarding_position,
    onboarding_position_guard,
    onboarding_callback_guard,
)


def get_employee_entry_point():
    return employee_start


def register_employee_states(states: dict):
    def emp_state(handler, pattern: str):
        return [
            CallbackQueryHandler(handler, pattern=pattern),
            CallbackQueryHandler(noop, pattern="^noop$"),
        ]

    # Онбординг
    states[ONBOARD_NAME] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_name_input),
        MessageHandler(~filters.TEXT & ~filters.COMMAND, onboarding_wrong_type_name),
        CallbackQueryHandler(onboarding_callback_guard),
    ]

    states[ONBOARD_POSITION] = [
        CallbackQueryHandler(onboarding_position, pattern=f"^{CB_POSITION_PREFIX}.*"),
        CallbackQueryHandler(onboarding_position_guard),
    ]

    # Главное меню
    states[MAIN_MENU] = emp_state(
        main_menu_callback,
        f"^{CB_START_SHIFT}$|^{CB_CHECKLIST}$|^{CB_PROGRESS}$|^{CB_BACK_MENU}$"
    )

    # Категории
    states[CATEGORY_SELECT] = emp_state(
        category_selection,
        f"^{CB_CATEGORY_PREFIX}.*|^{CB_BACK_MENU}$"
    )

    # Список задач
    states[CHECKLIST_VIEW] = emp_state(
        view_item,
        f"^{CB_ITEM_PREFIX}.*|^{CB_BACK_CATEGORIES}$|^{CB_BACK_MENU}$"
    )

    # Карточка задачи
    states[ITEM_DETAIL] = [
        CallbackQueryHandler(
            toggle_item_callback,
            pattern=(
                f"^{CB_TOGGLE_PREFIX}.*|"
                f"^{CB_PHOTO_PREFIX}.*|"
                f"^{CB_VIEW_PHOTO_PREFIX}.*|"
                f"^{CB_BACK_CATEGORIES}$|"
                f"^{CB_BACK_MENU}$"
            )
        ),
        CallbackQueryHandler(photo_cancel, pattern=f"^{CB_PHOTO_CANCEL}$"),
        CallbackQueryHandler(noop, pattern="^noop$"),
    ]

    # Прогресс
    states[PROGRESS_VIEW] = emp_state(
        progress_back,
        f"^{CB_BACK_MENU}$"
    )

    # Ожидание фото
    states[AWAIT_TASK_PHOTO] = [
        MessageHandler(filters.PHOTO, photo_input),
        MessageHandler(~filters.PHOTO & ~filters.COMMAND, photo_wrong_type),
        CallbackQueryHandler(photo_cancel, pattern=f"^{CB_PHOTO_CANCEL}$"),
        CallbackQueryHandler(photo_state_guard),
    ]

    # Регистрируем состояния из menu (включая выбор смены)
    register_menu_states(states)