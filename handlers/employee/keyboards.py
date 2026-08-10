from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu_keyboard(has_shift=False):
    keyboard = [
        [InlineKeyboardButton("✅ Отметиться на смене", callback_data="shift_mark")]
    ]
    if has_shift:
        keyboard.append([InlineKeyboardButton("📋 Мои чек-листы", callback_data="checklist")])
        keyboard.append([InlineKeyboardButton("📈 Мой прогресс", callback_data="progress")])
    return InlineKeyboardMarkup(keyboard)

def location_keyboard():
    keyboard = [
        [InlineKeyboardButton("🍸 Бар", callback_data="shift_bar")],
        [InlineKeyboardButton("🍳 Кухня", callback_data="shift_kitchen")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def checklist_keyboard(items, date):
    keyboard = []
    current_category = None
    for idx, item in enumerate(items):
        category = item.get('category', '')
        if category != current_category:
            current_category = category
            keyboard.append([InlineKeyboardButton(f"--- {current_category.upper()} ---", callback_data="noop")])
        status = "✅" if item.get('completed', False) else "⬜"
        callback = f"item_done_{idx}" if not item.get('completed', False) else f"item_undo_{idx}"
        keyboard.append([InlineKeyboardButton(f"{status} {item['text'][:30]}", callback_data=callback)])
    keyboard.append([InlineKeyboardButton("◀️ В главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

def progress_keyboard():
    keyboard = [[InlineKeyboardButton("◀️ В главное меню", callback_data="back_main")]]
    return InlineKeyboardMarkup(keyboard)