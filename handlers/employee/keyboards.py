from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .constants import CATEGORY_NAMES

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

def checklist_keyboard(items, category, back_callback="back_categories"):
    keyboard = []
    for item in items:
        status = "✅" if item['completed'] else "⬜"
        # Используем реальный id из БД
        callback = f"item_done_{item['id']}" if not item['completed'] else f"item_undo_{item['id']}"
        text = item['text'][:40] + "..." if len(item['text']) > 40 else item['text']
        keyboard.append([InlineKeyboardButton(f"{status} {text}", callback_data=callback)])
    keyboard.append([InlineKeyboardButton("◀️ Назад к категориям", callback_data=back_callback)])
    return InlineKeyboardMarkup(keyboard)

def progress_keyboard():
    keyboard = [[InlineKeyboardButton("◀️ В главное меню", callback_data="back_main")]]
    return InlineKeyboardMarkup(keyboard)