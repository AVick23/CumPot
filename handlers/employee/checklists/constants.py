# Состояния (используются в employee/__init__.py)
CATEGORY_SELECT = 11
CHECKLIST_VIEW = 5
ITEM_DETAIL = 6
PROGRESS_VIEW = 7
AWAIT_TASK_PHOTO = 8

# Callback data
CB_NOOP = "noop"
CB_CATEGORY_PREFIX = "cat:"
CB_ITEM_PREFIX = "item:"
CB_TOGGLE_PREFIX = "toggle:"
CB_PHOTO_PREFIX = "photo:"
CB_VIEW_PHOTO_PREFIX = "view_photo:"
CB_PHOTO_CANCEL = "photo_cancel"
CB_BACK_MENU = "back_menu"
CB_BACK_CATEGORIES = "back_cats"
CB_PHOTO_DONE = "photo_done"   # добавлено для подтверждения альбома (опционально)

# UI
CATEGORY_NAMES = {
    "opening": "☀️ Открытие",
    "daytime": "🌤 В течение дня",
    "closing": "🌙 Закрытие",
    "weekly": "📆 Недельные",
}
CATEGORY_ORDER = ["opening", "daytime", "closing", "weekly"]
LOCATIONS = {
    "bar": "🍸 Бар",
    "kitchen": "🍳 Кухня",
}
MSG_LIMIT = 3800