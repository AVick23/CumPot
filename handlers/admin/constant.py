# Состояния для админа
ADMIN_MAIN = 10
ADMIN_SHIFTS = 11
ADMIN_SELECT_EMPLOYEE = 20
ADMIN_CALENDAR = 35
ADMIN_DAY_PROGRESS = 36
ADMIN_EDIT_ITEMS = 22
ADMIN_EDIT_ITEM = 23
ADMIN_DELETE_ITEM = 24
ADMIN_ADD_ITEM_MODE = 25

# Состояния для добавления/редактирования
ADMIN_AWAIT_ITEM_TEXT = 26
ADMIN_AWAIT_ITEM_TYPE = 27
ADMIN_AWAIT_ITEM_LOCATION = 28
ADMIN_AWAIT_ITEM_CATEGORY = 29
ADMIN_AWAIT_ITEM_DAY = 30
ADMIN_AWAIT_EDIT_TEXT = 31

# Callback data для календаря
CB_ADMIN_MONTH_PREV = "admin_month_prev"
CB_ADMIN_MONTH_NEXT = "admin_month_next"
CB_ADMIN_DAY = "admin_day_"          # + день, например admin_day_15
CB_ADMIN_BACK_TO_CALENDAR = "admin_back_to_calendar"

# Остальные callback'и
CB_ADMIN_SHIFTS = "admin_shifts"
CB_ADMIN_PROGRESS = "admin_progress"
CB_ADMIN_EDIT = "admin_edit"
CB_ADMIN_BACK = "admin_back"
CB_ADMIN_EMPLOYEE = "admin_employee_"
CB_ADMIN_EDIT_ITEM = "admin_edit_item_"
CB_ADMIN_DELETE_ITEM = "admin_delete_item_"
CB_ADMIN_CONFIRM_DELETE = "admin_confirm_delete_"
CB_ADMIN_ADD_ITEM = "admin_add_item"
CB_ADMIN_EDIT_ITEMS = "admin_edit_items"
CB_ADMIN_ITEM_TYPE = "admin_item_type_"
CB_ADMIN_ITEM_LOCATION = "admin_item_location_"
CB_ADMIN_ITEM_CATEGORY = "admin_item_category_"
CB_ADMIN_ITEM_DAY = "admin_item_day_"
CB_ADMIN_CANCEL = "admin_cancel"