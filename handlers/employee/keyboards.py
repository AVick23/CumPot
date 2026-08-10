from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .constants import CATEGORY_NAMES, CB_ITEM_VIEW, CB_ITEM_TOGGLE

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

def categories_keyboard(available_categories):
    keyboard = []
    for cat in available_categories:
        label = CATEGORY_NAMES.get(cat, cat)
        keyboard.append([InlineKeyboardButton(label, callback_data=f"category_{cat}")])
    keyboard.append([InlineKeyboardButton("◀️ В главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

def checklist_keyboard(items):
    keyboard = []
    for item in items:
        text = item['text'][:30] + "..." if len(item['text']) > 30 else item['text']
        status_emoji = "✅" if item['completed'] else "⬜"
        keyboard.append([InlineKeyboardButton(f"{status_emoji} {text}", callback_data=f"{CB_ITEM_VIEW}{item['id']}")])
    keyboard.append([InlineKeyboardButton("◀️ Назад к категориям", callback_data="back_categories")])
    return InlineKeyboardMarkup(keyboard)

def item_detail_keyboard(item_id, is_completed):
    toggle_label = "✅ Выполнить" if not is_completed else "❌ Отменить"
    keyboard = [
        [InlineKeyboardButton(toggle_label, callback_data=f"{CB_ITEM_TOGGLE}{item_id}")],
        [InlineKeyboardButton("◀️ Назад к списку", callback_data="back_to_categories")],
    ]
    return InlineKeyboardMarkup(keyboard)

def progress_keyboard():
    keyboard = [[InlineKeyboardButton("◀️ В главное меню", callback_data="back_main")]]
    return InlineKeyboardMarkup(keyboard)