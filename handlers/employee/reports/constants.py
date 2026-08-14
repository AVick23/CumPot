# =========================================================
# STATES
# =========================================================

REPORT_SELECT_TYPE = 50          # выбор типа отчёта (открытие/закрытие)
REPORT_VIEW_DATE = 51            # просмотр отчёта за дату (календарь)
REPORT_VIEW_DETAIL = 52          # просмотр конкретного отчёта
REPORT_AWAIT_TEXT = 53           # ожидание текста нового отчёта
REPORT_CONFIRM_SAVE = 54         # подтверждение сохранения (опционально)


# =========================================================
# CALLBACK DATA
# =========================================================

CB_REPORT_BACK_MENU = "rep_back_menu"
CB_REPORT_OPENING = "rep_opening"
CB_REPORT_CLOSING = "rep_closing"
CB_REPORT_DATE_PREFIX = "rep_date:"       # + YYYYMMDD
CB_REPORT_PREV_MONTH = "rep_prev_month"
CB_REPORT_NEXT_MONTH = "rep_next_month"
CB_REPORT_CREATE = "rep_create"
CB_REPORT_VIEW = "rep_view"
CB_REPORT_CANCEL = "rep_cancel"
CB_REPORT_SAVE = "rep_save"


# =========================================================
# UI / DICTIONARIES
# =========================================================

MONTHS = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]
WEEKDAYS_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

REPORT_TYPE_LABELS = {
    "opening": "📋 Открытие",
    "closing": "🌙 Закрытие"
}

MSG_LIMIT = 4096  # максимальная длина сообщения Telegram