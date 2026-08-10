from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .constant import *
from ..employee.constants import CATEGORY_NAMES  # импортируем названия категорий
from datetime import datetime
import calendar

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

def calendar_keyboard(year, month, shift_days):
    """Создаёт клавиатуру-календарь на месяц."""
    keyboard = []
    month_name = calendar.month_name[month]
    keyboard.append([
        InlineKeyboardButton("◀️", callback_data=CB_ADMIN_MONTH_PREV),
        InlineKeyboardButton(f"{month_name} {year}", callback_data="noop"),
        InlineKeyboardButton("▶️", callback_data=CB_ADMIN_MONTH_NEXT),
    ])
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    keyboard.append([InlineKeyboardButton(day, callback_data="noop") for day in weekdays])
    first_day = datetime(year, month, 1)
    start_weekday = first_day.weekday()
    _, days_in_month = calendar.monthrange(year, month)
    row = []
    for _ in range(start_weekday):
        row.append(InlineKeyboardButton(" ", callback_data="noop"))
    for day in range(1, days_in_month + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        label = f"✅{day}" if date_str in shift_days else str(day)
        row.append(InlineKeyboardButton(label, callback_data=f"{CB_ADMIN_DAY}{date_str}"))
        if len(row) == 7:
            keyboard.append(row)
            row = []
    if row:
        while len(row) < 7:
            row.append(InlineKeyboardButton(" ", callback_data="noop"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("◀️ Выбрать другого сотрудника", callback_data=CB_ADMIN_BACK)])
    return InlineKeyboardMarkup(keyboard)

def progress_detail_keyboard(employee_id, date_str):
    keyboard = [
        [InlineKeyboardButton("◀️ Назад к календарю", callback_data=CB_ADMIN_BACK_TO_CALENDAR)],
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Новые клавиатуры для редактора ---

def edit_categories_keyboard(available_categories):
    keyboard = []
    for cat in available_categories:
        label = CATEGORY_NAMES.get(cat, cat)
        keyboard.append([InlineKeyboardButton(label, callback_data=f"{CB_ADMIN_EDIT_CATEGORY}{cat}")])
    keyboard.append([InlineKeyboardButton("➕ Добавить пункт", callback_data=CB_ADMIN_ADD_ITEM)])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data=CB_ADMIN_BACK)])
    return InlineKeyboardMarkup(keyboard)

def edit_items_list_keyboard(items, category):
    keyboard = []
    for item in items:
        text = item['text'][:30] + "..." if len(item['text']) > 30 else item['text']
        keyboard.append([
            InlineKeyboardButton(f"✏️ {text}", callback_data=f"{CB_ADMIN_EDIT_ITEM}{item['id']}"),
            InlineKeyboardButton("🗑️", callback_data=f"{CB_ADMIN_EDIT_DELETE}{item['id']}")
        ])
    keyboard.append([InlineKeyboardButton("◀️ Назад к категориям", callback_data=CB_ADMIN_EDIT_BACK)])
    return InlineKeyboardMarkup(keyboard)

def confirm_delete_keyboard(item_id):
    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить", callback_data=f"{CB_ADMIN_EDIT_CONFIRM_DELETE}{item_id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data=CB_ADMIN_EDIT_BACK)],
    ]
    return InlineKeyboardMarkup(keyboard)

def add_item_type_keyboard():
    keyboard = [
        [InlineKeyboardButton("📅 Ежедневная", callback_data=f"{CB_ADMIN_ITEM_TYPE}daily")],
        [InlineKeyboardButton("📆 Недельная", callback_data=f"{CB_ADMIN_ITEM_TYPE}weekly")],
        [InlineKeyboardButton("◀️ Отмена", callback_data=CB_ADMIN_CANCEL)],
    ]
    return InlineKeyboardMarkup(keyboard)

def add_item_location_keyboard():
    keyboard = [
        [InlineKeyboardButton("🍸 Бар", callback_data=f"{CB_ADMIN_ITEM_LOCATION}bar")],
        [InlineKeyboardButton("🍳 Кухня", callback_data=f"{CB_ADMIN_ITEM_LOCATION}kitchen")],
        [InlineKeyboardButton("◀️ Назад", callback_data=CB_ADMIN_BACK)],
    ]
    return InlineKeyboardMarkup(keyboard)

def add_item_category_keyboard():
    keyboard = [
        [InlineKeyboardButton("☀️ Открытие", callback_data=f"{CB_ADMIN_ITEM_CATEGORY}opening")],
        [InlineKeyboardButton("📅 В течение дня", callback_data=f"{CB_ADMIN_ITEM_CATEGORY}daytime")],
        [InlineKeyboardButton("🌙 Закрытие", callback_data=f"{CB_ADMIN_ITEM_CATEGORY}closing")],
        [InlineKeyboardButton("📆 Недельная", callback_data=f"{CB_ADMIN_ITEM_CATEGORY}weekly")],
        [InlineKeyboardButton("◀️ Назад", callback_data=CB_ADMIN_BACK)],
    ]
    return InlineKeyboardMarkup(keyboard)

def add_item_day_keyboard():
    keyboard = [
        [InlineKeyboardButton("ПН", callback_data=f"{CB_ADMIN_ITEM_DAY}0")],
        [InlineKeyboardButton("ВТ", callback_data=f"{CB_ADMIN_ITEM_DAY}1")],
        [InlineKeyboardButton("СР", callback_data=f"{CB_ADMIN_ITEM_DAY}2")],
        [InlineKeyboardButton("ЧТ", callback_data=f"{CB_ADMIN_ITEM_DAY}3")],
        [InlineKeyboardButton("ПТ", callback_data=f"{CB_ADMIN_ITEM_DAY}4")],
        [InlineKeyboardButton("СБ", callback_data=f"{CB_ADMIN_ITEM_DAY}5")],
        [InlineKeyboardButton("ВС", callback_data=f"{CB_ADMIN_ITEM_DAY}6")],
        [InlineKeyboardButton("◀️ Назад", callback_data=CB_ADMIN_BACK)],
    ]
    return InlineKeyboardMarkup(keyboard)