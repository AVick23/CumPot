# =========================================================
# STATES
# =========================================================

ADMIN_CALENDAR = 103
ADMIN_DAY_REPORT = 104

ADMIN_PHOTO_OVERVIEW = 130
ADMIN_PHOTO_LOCATION = 131
ADMIN_PHOTO_CATEGORY = 132


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

# Новый фотоотчёт
CB_PHOTO_REPORT = "photo_report"

# Legacy-кнопки, на случай старых callback
CB_SHOW_MEDIA_PREFIX = "media"

# Навигация по фотоотчёту
CB_PHOTO_LOC_PREFIX = "ploc"
CB_PHOTO_CAT_PREFIX = "pcat"

CB_PHOTO_ALL_LOC = "pallloc"
CB_PHOTO_ALL_CAT = "pallcat"

CB_PHOTO_TASK_PREFIX = "ptask"
CB_PHOTO_PAGE_PREFIX = "ppg"

CB_PHOTO_BACK_DAY = "pback_day"
CB_PHOTO_BACK_OVERVIEW = "pback_overview"
CB_PHOTO_BACK_LOC = "pback_loc"


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
    "bar": "🍸 Бар",
    "kitchen": "🍳 Кухня",
}

CATEGORY_ORDER = [
    "opening",
    "daytime",
    "closing",
    "weekly",
    "once",
]

CATEGORY_LABELS = {
    "opening": "☀️ Открытие",
    "daytime": "🌤 В течение дня",
    "closing": "🌙 Закрытие",
    "weekly": "📆 Недельные",
    "once": "📌 Одноразовые",
}

MSG_LIMIT = 3800

# Сколько медиа отправлять в одном альбоме
MEDIA_CHUNK_SIZE = 10

# Сколько задач с фото показывать на одной странице
PHOTO_PAGE_SIZE = 8

# Небольшая пауза между отправками альбомов разных задач,
# чтобы не упёрться в flood-limit Telegram
TASK_SEND_DELAY = 0.35