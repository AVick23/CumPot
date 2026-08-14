# Состояния для онбординга и главного меню
ONBOARD_NAME = 1
ONBOARD_POSITION = 2
MAIN_MENU = 3
SELECT_SHIFT_TYPE = 10   # ← исправлено, уникальное значение

# Callback data
CB_START_SHIFT = "start_shift"
CB_CHECKLIST = "checklist"
CB_PROGRESS = "progress"
CB_BACK_MENU = "back_menu"
CB_POSITION_PREFIX = "pos:"
CB_SHIFT_TYPE_PREFIX = "shift_type:"
CB_REPORTS = "reports"

# UI
LOCATIONS = {
    "bar": "🍸 Бар",
    "kitchen": "🍳 Кухня",
}
FULL_NAME_LIMIT = 100
MSG_LIMIT = 3800