# =========================================================
# STATES
# =========================================================

REPORT_SELECT_TYPE = 50
REPORT_VIEW_DATE = 51
REPORT_VIEW_DETAIL = 52
REPORT_AWAIT_TEXT = 53
REPORT_CONFIRM_SAVE = 54


# =========================================================
# CALLBACK DATA
# =========================================================

CB_REPORT_BACK_MENU = "rep_back_menu"
CB_REPORT_OPENING = "rep_opening"
CB_REPORT_CLOSING = "rep_closing"
CB_REPORT_DATE_PREFIX = "rep_date:"
CB_REPORT_PREV_MONTH = "rep_prev_month"
CB_REPORT_NEXT_MONTH = "rep_next_month"
CB_REPORT_CREATE = "rep_create"
CB_REPORT_VIEW = "rep_view"
CB_REPORT_CANCEL = "rep_cancel"
CB_REPORT_SAVE = "rep_save"

# Новые callback для просмотра предыдущих отчётов
CB_REPORT_PREV_OPENING = "rep_prev_opening"
CB_REPORT_PREV_CLOSING = "rep_prev_closing"


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

MSG_LIMIT = 4096