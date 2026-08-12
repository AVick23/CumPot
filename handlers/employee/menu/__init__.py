from telegram.ext import CallbackQueryHandler, MessageHandler, filters
from .handlers import (
    employee_start,
    onboarding_name_input,
    onboarding_wrong_type_name,
    onboarding_position,
    onboarding_position_guard,
    onboarding_callback_guard,
    main_menu_callback,
)
from .constants import (
    ONBOARD_NAME,
    ONBOARD_POSITION,
    MAIN_MENU,
    CB_START_SHIFT,
    CB_CHECKLIST,
    CB_PROGRESS,
    CB_BACK_MENU,
    CB_POSITION_PREFIX,
)


def register_menu_states(states: dict):
    """Регистрирует состояния онбординга и главного меню."""
    states[ONBOARD_NAME] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_name_input),
        MessageHandler(~filters.TEXT & ~filters.COMMAND, onboarding_wrong_type_name),
        CallbackQueryHandler(onboarding_callback_guard),
    ]
    states[ONBOARD_POSITION] = [
        CallbackQueryHandler(onboarding_position, pattern=f"^{CB_POSITION_PREFIX}.*"),
        CallbackQueryHandler(onboarding_position_guard),
    ]
    states[MAIN_MENU] = [
        CallbackQueryHandler(main_menu_callback, pattern=f"^{CB_START_SHIFT}$|^{CB_CHECKLIST}$|^{CB_PROGRESS}$|^{CB_BACK_MENU}$"),
        CallbackQueryHandler(lambda *_: None, pattern="^noop$"),
    ]


async def employee_entry(update, context):
    """Точка входа для сотрудника."""
    return await employee_start(update, context)