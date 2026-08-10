from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .constant import *

def admin_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📋 Смены сегодня", callback_data=CB_ADMIN_SHIFTS)],
        [InlineKeyboardButton("📊 Прогресс сотрудников", callback_data=CB_ADMIN_PROGRESS)],
        [InlineKeyboardButton("⚙️ Редактор чек-листов", callback_data=CB_ADMIN_EDIT)],
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_back_keyboard():
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data=CB_ADMIN_BACK)]]
    return InlineKeyboardMarkup(keyboard)

def employee_list_keyboard(employees):
    keyboard = []
    for emp in employees:
        name = f"{emp['first_name']} {emp['last_name']}" if emp['last_name'] else emp['first_name']
        keyboard.append([InlineKeyboardButton(name, callback_data=f"{CB_ADMIN_EMPLOYEE}{emp['tg_id']}")])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data=CB_ADMIN_BACK)])
    return InlineKeyboardMarkup(keyboard)

def edit_items_keyboard(items):
    keyboard = []
    for item in items:
        text = item['text'][:30] + "..." if len(item['text']) > 30 else item['text']
        keyboard.append([InlineKeyboardButton(f"✏️ {text}", callback_data=f"{CB_ADMIN_EDIT_ITEM}{item['id']}")])
    keyboard.append([InlineKeyboardButton("➕ Добавить пункт", callback_data=CB_ADMIN_ADD_ITEM)])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data=CB_ADMIN_BACK)])
    return InlineKeyboardMarkup(keyboard)

def edit_item_detail_keyboard(item_id):
    keyboard = [
        [InlineKeyboardButton("🗑️ Удалить", callback_data=f"{CB_ADMIN_DELETE_ITEM}{item_id}")],
        [InlineKeyboardButton("◀️ Назад к списку", callback_data=CB_ADMIN_EDIT_ITEMS)],
    ]
    return InlineKeyboardMarkup(keyboard)

def confirm_delete_keyboard(item_id):
    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить", callback_data=f"{CB_ADMIN_CONFIRM_DELETE}{item_id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data=CB_ADMIN_EDIT_ITEMS)],
    ]
    return InlineKeyboardMarkup(keyboard)

def add_item_keyboard():
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data=CB_ADMIN_EDIT_ITEMS)]]
    return InlineKeyboardMarkup(keyboard)