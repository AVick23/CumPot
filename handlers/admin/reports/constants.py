# =========================================================
# STATES
# =========================================================
ADMIN_CALENDAR = 103
ADMIN_DAY_REPORT = 104

ADMIN_PHOTO_OVERVIEW = 130
ADMIN_PHOTO_LOCATION = 131
ADMIN_PHOTO_CATEGORY = 132

ADMIN_TAXI_PHOTO_OVERVIEW = 140
ADMIN_TAXI_PHOTO_USER = 141


# =========================================================
# CALLBACK DATA
# =========================================================
CB_HOME = "home"
CB_TO_CALENDAR = "to_cal"

CB_PREV_MONTH = "prev"
CB_NEXT_MONTH = "next"

CB_DAY_PREFIX = "day"
CB_NOOP = "noop"

# Режимы отчёта
CB_REPORT_SHORT = "rep_short"
CB_REPORT_FULL = "rep_full"

# Фото в отчёте
CB_REPORT_PHOTOS_ON = "rep_photos_on"
CB_REPORT_PHOTOS_OFF = "rep_photos_off"

# Фотоотчёт чек-листов
CB_PHOTO_REPORT = "photo_report"

# Legacy
CB_SHOW_MEDIA_PREFIX = "media"

# Навигация по фотоотчёту чек-листов
CB_PHOTO_LOC_PREFIX = "ploc"
CB_PHOTO_CAT_PREFIX = "pcat"
CB_PHOTO_ALL_LOC = "pallloc"
CB_PHOTO_ALL_CAT = "pallcat"
CB_PHOTO_TASK_PREFIX = "ptask"
CB_PHOTO_PAGE_PREFIX = "ppg"

CB_PHOTO_BACK_DAY = "pback_day"
CB_PHOTO_BACK_OVERVIEW = "pback_overview"
CB_PHOTO_BACK_LOC = "pback_loc"

# Вкладки дневного отчёта
CB_TAB_CHECKLIST = "tab_checklist"
CB_TAB_SHIFT_REPORTS = "tab_shift_reports"
CB_TAB_TAXI = "tab_taxi"

# Фотоотчёт по такси
CB_TAXI_PHOTO_REPORT = "taxi_photo_report"
CB_TAXI_PHOTO_USER_PREFIX = "taxi_photo_user"
CB_TAXI_PHOTO_ALL = "taxi_photo_all"
CB_TAXI_PHOTO_BACK = "taxi_photo_back"


# =========================================================
# REPORT MODES
# =========================================================
REPORT_MODE_SHORT = "short"
REPORT_MODE_FULL = "full"


# =========================================================
# UI / DICTIONARIES
# =========================================================
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

MONTHS_GEN = [
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
]

WEEKDAYS_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

WEEKDAYS_FULL = [
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье",
]

LOCATIONS = {
    "bar": "Бар",
    "kitchen": "Кухня",
}

CATEGORY_ORDER = [
    "opening",
    "daytime",
    "closing",
    "weekly",
    "once",
]

CATEGORY_LABELS = {
    "opening": "Открытие",
    "daytime": "В течение дня",
    "closing": "Закрытие",
    "weekly": "Недельные",
    "once": "Разовые",
}

MSG_LIMIT = 3800

# Сколько медиа отправлять в одном альбоме
MEDIA_CHUNK_SIZE = 10

# Сколько задач с фото показывать на одной странице
PHOTO_PAGE_SIZE = 8

# Пауза между отправками альбомов
TASK_SEND_DELAY = 0.35