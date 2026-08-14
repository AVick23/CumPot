from telegram.ext import CallbackQueryHandler, MessageHandler, filters

from .handlers import (
    show_employees_list,
    employees_callback,
    employee_text_input,
)

from .constants import (
    EMPLOYEES_LIST,
    EMPLOYEE_DETAIL,
    EMPLOYEE_PROFILE,
    EMPLOYEE_RATE,
    EMPLOYEE_STATUS,
    EMPLOYEE_COMMENT,
    EMPLOYEE_SHIFTS,
    EMPLOYEE_TAXI,
    EMPLOYEE_REPORTS,
    EMPLOYEE_CHECKLISTS,
    EMPLOYEES_ANALYTICS,
    EMPLOYEE_AWAIT_RATE,
    EMPLOYEE_AWAIT_COMMENT,
    EMPLOYEE_DELETE_CONFIRM,          # НОВОЕ
)


def register_employee_states(states: dict):
    states[EMPLOYEES_LIST] = [
        CallbackQueryHandler(employees_callback),
    ]

    states[EMPLOYEE_DETAIL] = [
        CallbackQueryHandler(employees_callback),
    ]

    states[EMPLOYEE_PROFILE] = [
        CallbackQueryHandler(employees_callback),
    ]

    states[EMPLOYEE_RATE] = [
        CallbackQueryHandler(employees_callback),
    ]

    states[EMPLOYEE_STATUS] = [
        CallbackQueryHandler(employees_callback),
    ]

    states[EMPLOYEE_COMMENT] = [
        CallbackQueryHandler(employees_callback),
    ]

    states[EMPLOYEE_SHIFTS] = [
        CallbackQueryHandler(employees_callback),
    ]

    states[EMPLOYEE_TAXI] = [
        CallbackQueryHandler(employees_callback),
    ]

    states[EMPLOYEE_REPORTS] = [
        CallbackQueryHandler(employees_callback),
    ]

    states[EMPLOYEE_CHECKLISTS] = [
        CallbackQueryHandler(employees_callback),
    ]

    states[EMPLOYEES_ANALYTICS] = [
        CallbackQueryHandler(employees_callback),
    ]

    states[EMPLOYEE_AWAIT_RATE] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, employee_text_input),
        CallbackQueryHandler(employees_callback),
    ]

    states[EMPLOYEE_AWAIT_COMMENT] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, employee_text_input),
        CallbackQueryHandler(employees_callback),
    ]

    # НОВОЕ СОСТОЯНИЕ ДЛЯ ПОДТВЕРЖДЕНИЯ УДАЛЕНИЯ
    states[EMPLOYEE_DELETE_CONFIRM] = [
        CallbackQueryHandler(employees_callback),
    ]