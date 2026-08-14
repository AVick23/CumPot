from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .constants import (
    CB_EMPLOYEES_BACK,
    CB_EMPLOYEES_REPORT_ALL,
    CB_EMPLOYEE_DETAIL_PREFIX,
    CB_EMPLOYEE_EDIT_STATUS_PREFIX,
    CB_EMPLOYEE_EDIT_COMMENT_PREFIX,
    CB_EMPLOYEE_EDIT_RATE_PREFIX,
    CB_EMPLOYEE_REPORT_PREFIX,
    CB_EMPLOYEE_CANCEL,
    STATUSES,
)

def employees_list_keyboard(users: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    for user in users:
        name = user.get("full_name") or user.get("first_name") or f"ID {user['tg_id']}"
        buttons.append([InlineKeyboardButton(name, callback_data=f"{CB_EMPLOYEE_DETAIL_PREFIX}{user['tg_id']}")])
    buttons.append([InlineKeyboardButton("📊 Отчёт по сотрудникам", callback_data=CB_EMPLOYEES_REPORT_ALL)])
    buttons.append([InlineKeyboardButton("◀️ Назад", callback_data=CB_EMPLOYEES_BACK)])
    return InlineKeyboardMarkup(buttons)

def employee_detail_keyboard(user_id: int, current_status: str, current_rate: float) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"Статус: {current_status}", callback_data=f"{CB_EMPLOYEE_EDIT_STATUS_PREFIX}{user_id}")],
        [InlineKeyboardButton(f"Ставка: {current_rate:.2f} ₽/час", callback_data=f"{CB_EMPLOYEE_EDIT_RATE_PREFIX}{user_id}")],
        [InlineKeyboardButton("✏️ Комментарий", callback_data=f"{CB_EMPLOYEE_EDIT_COMMENT_PREFIX}{user_id}")],
        [InlineKeyboardButton("📊 Отчёт по сотруднику", callback_data=f"{CB_EMPLOYEE_REPORT_PREFIX}{user_id}")],
        [InlineKeyboardButton("◀️ Назад к списку", callback_data=CB_EMPLOYEES_BACK)],
    ]
    return InlineKeyboardMarkup(buttons)

def edit_status_keyboard(user_id: int) -> InlineKeyboardMarkup:
    buttons = []
    for status in STATUSES:
        buttons.append([InlineKeyboardButton(status, callback_data=f"emp_set_status:{user_id}:{status}")])
    buttons.append([InlineKeyboardButton("✖️ Отмена", callback_data=CB_EMPLOYEE_CANCEL)])
    return InlineKeyboardMarkup(buttons)

def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("✖️ Отмена", callback_data=CB_EMPLOYEE_CANCEL)]])