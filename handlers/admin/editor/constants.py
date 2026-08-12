# =========================================================
# STATES
# =========================================================

ADMIN_EDIT_LOCATION = 105
ADMIN_EDIT_CATEGORY = 106
ADMIN_EDIT_ITEMS = 107
ADMIN_ITEM_DETAIL = 108
ADMIN_DELETE_CONFIRM = 109
ADMIN_ADD_DAY = 110

ADMIN_AWAIT_NEW_TEXT = 111
ADMIN_AWAIT_EDIT_TEXT = 112
ADMIN_AWAIT_ITEM_TYPE = 113
ADMIN_AWAIT_DATE = 114
ADMIN_AWAIT_HOUR = 115
ADMIN_AWAIT_MINUTE = 116
ADMIN_AWAIT_PHOTO_FLAG = 117
ADMIN_AWAIT_NOTIFICATION_FLAG = 118
ADMIN_AWAIT_DAYS = 119

# Оставлены для совместимости и возможного расширения
ADMIN_EDIT_TOGGLE_PHOTO = 120
ADMIN_EDIT_TOGGLE_NOTIFICATION = 121
ADMIN_EDIT_CHANGE_TIME = 122
ADMIN_EDIT_CHANGE_DATE = 123


# =========================================================
# CALLBACK DATA
# =========================================================

CB_HOME = "home"

CB_TO_EDIT = "nav_loc"
CB_TO_CATEGORIES = "nav_cats"
CB_TO_ITEMS = "nav_items"

CB_LOC_PREFIX = "loc"
CB_CAT_PREFIX = "cat"
CB_PAGE_PREFIX = "pg"
CB_ITEM_PREFIX = "item"

CB_EDIT_ITEM_PREFIX = "edit_text"
CB_DELETE_ITEM_PREFIX = "del"
CB_CONFIRM_DELETE_PREFIX = "delok"

CB_ADD = "add"
CB_ADD_PICK = "add_pick"

CB_CANCEL = "cancel"
CB_CANCEL_EDIT = "cancel_edit"
CB_ADD_BACK_TEXT = "add_back_text"

# Тип задачи, если понадобится отдельный выбор
CB_ITEM_TYPE_PREFIX = "type"

# Дата / время
CB_DATE_PREFIX = "date"
CB_MONTH_PREV = "month_prev"
CB_MONTH_NEXT = "month_next"

CB_HOUR_PREFIX = "hour"
CB_MINUTE_PREFIX = "min"

# Флаги при создании
CB_PHOTO_FLAG_PREFIX = "photo"
CB_NOTIF_FLAG_PREFIX = "notif"
CB_FLAGS_SKIP = "flags_skip"

# Редактирование карточки
CB_TOGGLE_PHOTO = "tphoto"
CB_TOGGLE_NOTIFICATION = "tnotif"
CB_CHANGE_TIME = "time"
CB_CHANGE_DATE = "eddate"
CB_BACK_FROM_EDIT = "back_edit"

# Дни недели
CB_DAY_TOGGLE_PREFIX = "day"
CB_DAY_PRESET_PREFIX = "preset"
CB_DAYS_SAVE = "days_save"
CB_DAYS_CANCEL = "days_cancel"

# Совместимость со старой логикой
CB_ADD_DAY_PREFIX = "eddays"


# =========================================================
# UI / DICTIONARIES
# =========================================================

LOCATIONS = {
    "bar": "Бар",
    "kitchen": "Кухня",
}

DAILY_CATEGORIES = [
    ("opening", "Открытие"),
    ("daytime", "В течение дня"),
    ("closing", "Закрытие"),
]

CATEGORY_LABELS = {
    "opening": "Открытие",
    "daytime": "В течение дня",
    "closing": "Закрытие",
    "weekly": "Недельные",
    "once": "Разовые",
}

WEEKDAYS_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

MONTHS = [
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
]

PAGE_SIZE = 8
TEXT_LIMIT = 200
MSG_LIMIT = 3800