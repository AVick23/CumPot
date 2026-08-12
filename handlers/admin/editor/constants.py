# Состояния
ADMIN_EDIT_LOCATION = 105
ADMIN_EDIT_CATEGORY = 106
ADMIN_EDIT_ITEMS = 107
ADMIN_ITEM_DETAIL = 108
ADMIN_DELETE_CONFIRM = 109
ADMIN_ADD_DAY = 110
ADMIN_AWAIT_NEW_TEXT = 111
ADMIN_AWAIT_EDIT_TEXT = 112

ADMIN_AWAIT_ITEM_TYPE = 113       # выбор типа задачи (daily/weekly/once)
ADMIN_AWAIT_DUE_DATE = 114        # ввод даты для once
ADMIN_AWAIT_PHOTO_FLAG = 115      # требует ли фото
ADMIN_AWAIT_NOTIFICATION_FLAG = 116  # требует ли уведомления

# Callback data
CB_HOME = "home"
CB_TO_EDIT = "to_edit"
CB_TO_CATEGORIES = "to_cats"
CB_TO_ITEMS = "to_items"
CB_LOC_PREFIX = "loc"
CB_CAT_PREFIX = "cat"
CB_PAGE_PREFIX = "pg"
CB_ITEM_PREFIX = "item"
CB_EDIT_ITEM_PREFIX = "edit_item"
CB_DELETE_ITEM_PREFIX = "del_item"
CB_CONFIRM_DELETE_PREFIX = "confirm_del"
CB_ADD = "add"
CB_ADD_DAY_PREFIX = "add_day"
CB_ADD_BACK_TEXT = "add_back_text"
CB_CANCEL = "cancel"
CB_CANCEL_EDIT = "cancel_edit"

# Новые callback'и для расширенного добавления
CB_ITEM_TYPE_PREFIX = "item_type:"      # + daily/weekly/once
CB_DUE_DATE_BACK = "due_date_back"
CB_PHOTO_FLAG_PREFIX = "photo:"         # + yes/no
CB_NOTIF_FLAG_PREFIX = "notif:"         # + yes/no
CB_FLAGS_SKIP = "flags_skip"

# UI
LOCATIONS = {"bar": "🍸 Бар", "kitchen": "🍳 Кухня"}
DAILY_CATEGORIES = [
    ("opening", "☀️ Открытие"),
    ("daytime", "🌤 В течение дня"),
    ("closing", "🌙 Закрытие"),
]
CATEGORY_LABELS = {
    "opening": "☀️ Открытие",
    "daytime": "🌤 В течение дня",
    "closing": "🌙 Закрытие",
    "weekly": "📆 Недельные",
}
WEEKDAYS_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
PAGE_SIZE = 8
TEXT_LIMIT = 200
MSG_LIMIT = 3800