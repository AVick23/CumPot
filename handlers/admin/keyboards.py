from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def admin_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("📋 Смены сегодня", callback_data="admin_shifts")],
        [InlineKeyboardButton("📊 Прогресс сотрудников", callback_data="admin_progress")],
        [InlineKeyboardButton("⚙️ Редактор чек-листов", callback_data="admin_edit")],
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_back_keyboard():
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]]
    return InlineKeyboardMarkup(keyboard)