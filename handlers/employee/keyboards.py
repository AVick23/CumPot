from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("✅ Отметиться на смене", callback_data="shift_mark")],
        [InlineKeyboardButton("📋 Мои чек-листы", callback_data="checklist")],
        [InlineKeyboardButton("📈 Мой прогресс", callback_data="progress")],
    ]
    return InlineKeyboardMarkup(keyboard)

def location_keyboard():
    keyboard = [
        [InlineKeyboardButton("🍸 Бар", callback_data="shift_bar")],
        [InlineKeyboardButton("🍳 Кухня", callback_data="shift_kitchen")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def checklist_keyboard(items, date):
    # items - список пунктов с полями id, text, completed (0/1), category
    keyboard = []
    current_category = None
    for item in items:
        if item['category'] != current_category:
            current_category = item['category']
            # Добавляем заголовок категории (не кликабельный)
            keyboard.append([InlineKeyboardButton(f"--- {current_category.upper()} ---", callback_data="noop")])
        status = "✅" if item['completed'] else "⬜"
        callback = f"item_done_{item['id']}" if not item['completed'] else f"item_undo_{item['id']}"
        keyboard.append([InlineKeyboardButton(f"{status} {item['text'][:30]}", callback_data=callback)])
    keyboard.append([InlineKeyboardButton("◀️ В главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

def progress_keyboard():
    keyboard = [[InlineKeyboardButton("◀️ В главное меню", callback_data="back_main")]]
    return InlineKeyboardMarkup(keyboard)