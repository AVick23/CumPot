# Состояния для ConversationHandler
SELECT_LOCATION = 1
MAIN_MENU = 2
CHECKLIST_VIEW = 3
MARK_ITEM = 4
PROGRESS_VIEW = 5
CATEGORY_SELECT = 6
ITEM_DETAIL = 7

# Callback data для кнопок
CB_SHIFT_MARK = "shift_mark"
CB_SHIFT_BAR = "shift_bar"
CB_SHIFT_KITCHEN = "shift_kitchen"
CB_CHECKLIST = "checklist"
CB_PROGRESS = "progress"
CB_ITEM_VIEW = "item_view_"
CB_ITEM_TOGGLE = "item_toggle_"
CB_BACK_MAIN = "back_main"
CB_CATEGORY = "category_"
CB_BACK_CATEGORIES = "back_categories"
CB_BACK_TO_CATEGORIES = "back_to_categories"

# Читаемые названия категорий
CATEGORY_NAMES = {
    "opening": "☀️ Открытие",
    "daytime": "📅 В течение дня",
    "closing": "🌙 Закрытие",
    "weekly": "📆 Недельная задача",
}