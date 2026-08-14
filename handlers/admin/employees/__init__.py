from telegram.ext import CallbackQueryHandler, MessageHandler, filters
from .handlers import (
    show_employees_list,
    employees_callback,
    employee_text_input,
)
from .constants import (
    EMPLOYEES_LIST,
    EMPLOYEE_DETAIL,
    EMPLOYEE_EDIT_STATUS,
    EMPLOYEE_EDIT_COMMENT,
    EMPLOYEE_EDIT_RATE,
)

def register_employee_states(states: dict):
    states[EMPLOYEES_LIST] = [CallbackQueryHandler(employees_callback)]
    states[EMPLOYEE_DETAIL] = [CallbackQueryHandler(employees_callback)]
    states[EMPLOYEE_EDIT_STATUS] = [CallbackQueryHandler(employees_callback)]
    states[EMPLOYEE_EDIT_COMMENT] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, employee_text_input),
        CallbackQueryHandler(employees_callback),
    ]
    states[EMPLOYEE_EDIT_RATE] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, employee_text_input),
        CallbackQueryHandler(employees_callback),
    ]