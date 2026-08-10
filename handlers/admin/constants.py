# Состояния админа
ADMIN_MAIN = 100
ADMIN_SHIFTS = 101
ADMIN_EMPLOYEES = 102
ADMIN_CALENDAR = 103
ADMIN_DAY_PROGRESS = 104
ADMIN_EDIT_LOCATION = 105
ADMIN_EDIT_CATEGORY = 106
ADMIN_EDIT_ITEMS = 107
ADMIN_ITEM_DETAIL = 108
ADMIN_DELETE_CONFIRM = 109
ADMIN_ADD_DAY = 110
ADMIN_AWAIT_NEW_TEXT = 111
ADMIN_AWAIT_EDIT_TEXT = 112

# Callback data (без пробелов!)
CB_NOOP = "noop"
CB_HOME = "home"
CB_SHIFTS = "shifts"
CB_EMPLOYEES = "employees"
CB_EDIT = "edit"
CB_EMP_PREFIX = "user:"
CB_PREV_MONTH = "prev"
CB_NEXT_MONTH = "next"
CB_DAY_PREFIX = "day:"
CB_TO_EMPLOYEES = "to_users"
CB_TO_CALENDAR = "to_cal"
CB_TO_EDIT = "to_edit"
CB_TO_CATEGORIES = "to_cats"
CB_TO_ITEMS = "to_items"
CB_LOC_PREFIX = "loc:"
CB_CAT_PREFIX = "cat:"
CB_PAGE_PREFIX = "pg:"
CB_ITEM_PREFIX = "item:"
CB_EDIT_ITEM_PREFIX = "edit_item:"
CB_DELETE_ITEM_PREFIX = "del_item:"
CB_CONFIRM_DELETE_PREFIX = "confirm_del:"
CB_ADD = "add"
CB_ADD_DAY_PREFIX = "add_day:"
CB_ADD_BACK_TEXT = "add_back_text"
CB_CANCEL = "cancel"
CB_CANCEL_EDIT = "cancel_edit"

# UI константы
PAGE_SIZE = 8
TEXT_LIMIT = 200
MSG_LIMIT = 3800

LOCATIONS = {
    "bar": "🍸 Бар",
    "kitchen": "🍳 Кухня",
}

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

CATEGORY_ORDER = ["opening", "daytime", "closing", "weekly"]

WEEKDAYS_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

MONTHS = [
    "Январь", "Февраль", "Март", "Апрель",
    "Май", "Июнь", "Июль", "Август",
    "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]

MONTHS_GEN = [
    "января", "февраля", "марта", "апреля",
    "мая", "июня", "июля", "августа",
    "сентября", "октября", "ноября", "декабря",
]