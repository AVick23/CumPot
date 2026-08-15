from telegram.ext import CallbackQueryHandler, MessageHandler, filters

from .menu.handlers import (
    employee_start,
    main_menu_callback,
    shift_type_selection,
    onboarding_name_input,
    onboarding_wrong_type_name,
    onboarding_position,
    onboarding_position_guard,
    onboarding_callback_guard,
)
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

# Импорт для отчётов и профиля
from .reports import register_report_states
from .profile import register_profile_states

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
    CB_SHIFT_TYPE_PREFIX,
    CB_REPORTS,
    CB_PROFILE,
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


def get_employee_entry_point():
    return employee_start


def register_employee_states(states: dict):
    def emp_state(handler, pattern: str):
        return [
            CallbackQueryHandler(handler, pattern=pattern),
            CallbackQueryHandler(noop, pattern="^noop$"),
        ]

    # Онбординг: ФИО
    states[ONBOARD_NAME] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_name_input),
        MessageHandler(~filters.TEXT & ~filters.COMMAND, onboarding_wrong_type_name),
        CallbackQueryHandler(onboarding_callback_guard),
    ]

    # Онбординг: позиция
    states[ONBOARD_POSITION] = [
        CallbackQueryHandler(onboarding_position, pattern=f"^{CB_POSITION_PREFIX}.*"),
        CallbackQueryHandler(onboarding_position_guard),
    ]

    # Главное меню – убрали CB_TAXI
    states[MAIN_MENU] = [
        CallbackQueryHandler(
            main_menu_callback,
            pattern=(
                f"^{CB_START_SHIFT}$|^{CB_CHECKLIST}$|^{CB_PROGRESS}$|"
                f"^{CB_BACK_MENU}$|^{CB_REPORTS}$|^{CB_PROFILE}$"
            )
        ),
        CallbackQueryHandler(noop, pattern="^noop$"),
    ]

    # Выбор смены
    states[SELECT_SHIFT_TYPE] = [
        CallbackQueryHandler(shift_type_selection, pattern=f"^{CB_SHIFT_TYPE_PREFIX}.*|^{CB_BACK_MENU}$"),
        CallbackQueryHandler(noop, pattern="^noop$"),
    ]

    # Категории
    states[CATEGORY_SELECT] = [
        CallbackQueryHandler(category_selection, pattern=f"^{CB_CATEGORY_PREFIX}.*|^{CB_BACK_MENU}$"),
        CallbackQueryHandler(noop, pattern="^noop$"),
    ]

    # Список задач
    states[CHECKLIST_VIEW] = [
        CallbackQueryHandler(view_item, pattern=f"^{CB_ITEM_PREFIX}.*|^{CB_BACK_CATEGORIES}$|^{CB_BACK_MENU}$"),
        CallbackQueryHandler(noop, pattern="^noop$"),
    ]

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
    states[PROGRESS_VIEW] = [
        CallbackQueryHandler(progress_back, pattern=f"^{CB_BACK_MENU}$"),
        CallbackQueryHandler(noop, pattern="^noop$"),
    ]

    # Ожидание фото
    states[AWAIT_TASK_PHOTO] = [
        MessageHandler(filters.PHOTO, photo_input),
        MessageHandler(~filters.PHOTO & ~filters.COMMAND, photo_wrong_type),
        CallbackQueryHandler(photo_cancel, pattern=f"^{CB_PHOTO_CANCEL}$"),
        CallbackQueryHandler(photo_state_guard),
    ]

    # Регистрируем состояния для отчётов и профиля
    register_report_states(states)
    register_profile_states(states)