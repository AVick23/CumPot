# =========================================================
# STATES
# =========================================================

CATEGORY_SELECT = 11
CHECKLIST_VIEW = 5
ITEM_DETAIL = 6
PROGRESS_VIEW = 7
AWAIT_TASK_PHOTO = 8


# =========================================================
# CALLBACK DATA
# =========================================================

CB_NOOP = "noop"

CB_CATEGORY_PREFIX = "cat:"
CB_ITEM_PREFIX = "item:"
CB_TOGGLE_PREFIX = "toggle:"
CB_PHOTO_ADD_PREFIX = "photo_add:"       # добавить фото (или выполнить с фото)
CB_PHOTO_REPLACE_PREFIX = "photo_replace:" # заменить фото
CB_VIEW_PHOTO_PREFIX = "view_photo:"

CB_PHOTO_CANCEL = "photo_cancel"
CB_PHOTO_DONE = "photo_done"

CB_BACK_MENU = "back_menu"
CB_BACK_CATEGORIES = "back_cats"


# =========================================================
# UI / DICTIONARIES
# =========================================================

CATEGORY_NAMES = {
    "opening": "☀️ Открытие",
    "daytime": "🌤 В течение дня",
    "closing": "🌙 Закрытие",
    "weekly": "📆 Недельные",
    "once": "📌 Одноразовые",
}

CATEGORY_ORDER = [
    "opening",
    "daytime",
    "closing",
    "weekly",
    "once",
]

LOCATIONS = {
    "bar": "🍸 Бар",
    "kitchen": "🍳 Кухня",
}

MSG_LIMIT = 3800
MEDIA_CHUNK_SIZE = 10