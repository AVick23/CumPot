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

CB_NOOP = "noop"

CB_REPORT_BACK_MENU = "rep_back_menu"
CB_REPORT_TO_CALENDAR = "rep_to_calendar"

CB_REPORT_TYPE_PREFIX = "rep_type:"
CB_REPORT_DATE_PREFIX = "rep_date:"

CB_REPORT_PREV_MONTH = "rep_prev_month"
CB_REPORT_NEXT_MONTH = "rep_next_month"

CB_REPORT_CREATE = "rep_create"
CB_REPORT_EDIT = "rep_edit"
CB_REPORT_VIEW = "rep_view"

CB_REPORT_TEMPLATE = "rep_template"

CB_REPORT_SAVE = "rep_save"
CB_REPORT_REENTER = "rep_reenter"
CB_REPORT_CANCEL = "rep_cancel"

CB_REPORT_PREV_REPORT = "rep_prev_report"


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

REPORT_TYPES = ["opening", "closing"]

REPORT_TYPE_LABELS = {
    "opening": "📋 Открытие",
    "closing": "🌙 Закрытие",
}

MSG_LIMIT = 4096
REPORT_PREVIEW_LIMIT = 700


# =========================================================
# REPORT TEMPLATES
# =========================================================

REPORT_TEMPLATES = {
    "opening": (
        "Влажность в помещении: \n"
        "В эспрессо: \n"
        "Тдс - \n"
        "Температура групп - \n"
        "Помол - \n"
        "Давление - \n"
        "Рецепт: \n"
        "В основе: \n"
        "В молоке: \n"
        "На фильтре: \n"
        "Стоп-лист: "
    ),

    "closing": (
        "Влажность в помещении: \n"
        "Стопы: \n"
        "Эспрессо, вода и заготовки по бару: \n"
        "Рецепт по завершении: \n"
        "Заготовки бар: \n"
        "Рекомендации по фильтру: \n"
        "Еда: \n"
        "Заготовки для еды: \n"
        "Блюда: \n"
        "Go-list: \n"
        "График уборки / полив цветов: \n"
        "Полы мылись: \n"
        "Примечания: "
    ),
}