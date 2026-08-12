# Состояния
ADMIN_EDIT_LOCATION = 105
ADMIN_EDIT_CATEGORY = 106
ADMIN_EDIT_ITEMS = 107
ADMIN_ITEM_DETAIL = 108
ADMIN_DELETE_CONFIRM = 109
ADMIN_ADD_DAY = 110
ADMIN_AWAIT_NEW_TEXT = 111
ADMIN_AWAIT_EDIT_TEXT = 112

ADMIN_AWAIT_ITEM_TYPE = 113       # выбор типа (daily/weekly/once)
ADMIN_AWAIT_DATE = 114            # выбор даты для once
ADMIN_AWAIT_HOUR = 115            # выбор часа
ADMIN_AWAIT_MINUTE = 116          # выбор минуты
ADMIN_AWAIT_PHOTO_FLAG = 117      # требует ли фото
ADMIN_AWAIT_NOTIFICATION_FLAG = 118  # требует ли уведомления
ADMIN_AWAIT_DAYS = 119            # выбор нескольких дней недели

# Состояния для редактирования в карточке
ADMIN_EDIT_TOGGLE_PHOTO = 120
ADMIN_EDIT_TOGGLE_NOTIFICATION = 121
ADMIN_EDIT_CHANGE_TIME = 122

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
CB_CANCEL = "cancel"
CB_CANCEL_EDIT = "cancel_edit"
CB_ADD_BACK_TEXT = "add_back_text"

# Новые для даты, времени, флагов
CB_ITEM_TYPE_PREFIX = "item_type:"      # + daily/weekly/once
CB_DATE_PREFIX = "date:"                # + YYYY-MM-DD
CB_MONTH_PREV = "month_prev"
CB_MONTH_NEXT = "month_next"
CB_HOUR_PREFIX = "hour:"                # + 0-23
CB_MINUTE_PREFIX = "minute:"            # + 0,5,10,...55
CB_PHOTO_FLAG_PREFIX = "photo:"         # + yes/no
CB_NOTIF_FLAG_PREFIX = "notif:"         # + yes/no
CB_FLAGS_SKIP = "flags_skip"

# Для редактирования в карточке
CB_TOGGLE_PHOTO = "toggle_photo:"
CB_TOGGLE_NOTIFICATION = "toggle_notif:"
CB_CHANGE_TIME = "change_time:"
CB_BACK_FROM_EDIT = "back_from_edit"

# Новое для множественного выбора дней
CB_DAY_TOGGLE_PREFIX = "day_toggle:"    # + день (0-6)
CB_DAYS_CONFIRM = "days_confirm"
CB_DAYS_CANCEL = "days_cancel"

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
    "once": "📌 Одноразовые",       # добавлено
}
WEEKDAYS_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
          "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
PAGE_SIZE = 8
TEXT_LIMIT = 200
MSG_LIMIT = 3800