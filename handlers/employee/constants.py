# Состояния сотрудника
ONBOARD_NAME = 1
ONBOARD_POSITION = 2
MAIN_MENU = 3
CATEGORY_SELECT = 4
CHECKLIST_VIEW = 5
ITEM_DETAIL = 6
PROGRESS_VIEW = 7
END_SHIFT_CONFIRM = 8

# Callback data
CB_NOOP = "noop"

CB_START_SHIFT = "start_shift"
CB_END_SHIFT = "end_shift"

CB_END_SHIFT_CONFIRM = "end_confirm"
CB_END_SHIFT_CANCEL = "end_cancel"

CB_CHECKLIST = "checklist"
CB_PROGRESS = "progress"

CB_POSITION_PREFIX = "pos:"
CB_CATEGORY_PREFIX = "cat:"
CB_ITEM_PREFIX = "item:"
CB_TOGGLE_PREFIX = "toggle:"

CB_BACK_MENU = "back_menu"
CB_BACK_CATEGORIES = "back_cats"

# UI
LOCATIONS = {
    "bar": "🍸 Бар",
    "kitchen": "🍳 Кухня",
}

CATEGORY_NAMES = {
    "opening": "☀️ Открытие",
    "daytime": "🌤 В течение дня",
    "closing": "🌙 Закрытие",
    "weekly": "📆 Недельные",
}

CATEGORY_ORDER = ["opening", "daytime", "closing", "weekly"]

MSG_LIMIT = 3800
FULL_NAME_LIMIT = 100