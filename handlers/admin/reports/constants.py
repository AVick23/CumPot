# =========================================================
# STATES
# =========================================================

ADMIN_CALENDAR = 103
ADMIN_DAY_REPORT = 104


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

# Отправка медиа
CB_SHOW_MEDIA_PREFIX = "media"


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

# Сколько фото отправлять за один раз и сколько максимум
MEDIA_CHUNK_SIZE = 10
MEDIA_SEND_LIMIT = 30