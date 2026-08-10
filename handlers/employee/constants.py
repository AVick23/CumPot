# Состояния для ConversationHandler
SELECT_LOCATION = 1
MAIN_MENU = 2
CHECKLIST_VIEW = 3
MARK_ITEM = 4
PROGRESS_VIEW = 5
CATEGORY_SELECT = 6  # новое состояние

# Callback data для кнопок
CB_SHIFT_MARK = "shift_mark"
CB_SHIFT_BAR = "shift_bar"
CB_SHIFT_KITCHEN = "shift_kitchen"
CB_CHECKLIST = "checklist"
CB_PROGRESS = "progress"
CB_ITEM_DONE = "item_done_"
CB_ITEM_UNDO = "item_undo_"
CB_BACK_MAIN = "back_main"
CB_CATEGORY = "category_"  # префикс для выбора категории
CB_BACK_CATEGORIES = "back_categories"

# ------------------------------------------------------------
# ВРЕМЕННЫЕ ХАРДКОДНЫЕ ЧЕК-ЛИСТЫ (для демонстрации)
# ------------------------------------------------------------

# Ежедневные задачи для БАРА
BAR_DAILY_ITEMS = [
    {"category": "opening", "text": "Включить свет и электричество (рубильники 10-16, 23-29)"},
    {"category": "opening", "text": "Включить бойлер, кофемашину, кофемолку, ледогенератор, свет витрины, кассу, колонку"},
    {"category": "opening", "text": "Открыть кассовую смену и внести наличные"},
    {"category": "opening", "text": "Включить музыку"},
    {"category": "opening", "text": "Проверить витрину на просрочку"},
    {"category": "opening", "text": "Настроить кофе (фильтр, эспрессо)"},
    {"category": "opening", "text": "Подготовить молочную систему (контейнер с молоком)"},
    {"category": "opening", "text": "Убрать заготовки из холодильника, проверить сроки"},
    {"category": "daytime", "text": "Проверить гостевые зоны (подушки, пледы, салфетницы)"},
    {"category": "daytime", "text": "Полить цветы (если сухо)"},
    {"category": "closing", "text": "Помыть барный инвентарь (холдеры, питчеры, ложки, ножи, сито, чайники, воронки)"},
    {"category": "closing", "text": "Очистить кофемашину (входные группы, стимеры, поддон)"},
    {"category": "closing", "text": "Почистить кофемолки (эспрессо и фильтр)"},
    {"category": "closing", "text": "Промыть молочную систему (Easy Milk)"},
    {"category": "closing", "text": "Убрать и промаркировать заготовки"},
    {"category": "closing", "text": "Протереть рабочие поверхности и выключить ледогенератор"},
]

# Ежедневные задачи для КУХНИ
KITCHEN_DAILY_ITEMS = [
    {"category": "opening", "text": "Поставить круассаны на расстойку (07:00)"},
    {"category": "opening", "text": "Подготовить яйца пашот (07:30)"},
    {"category": "opening", "text": "Проверить заготовки для блюд (08:00)"},
    {"category": "opening", "text": "Проверить овощи, фрукты, зелень на плесень (08:30)"},
    {"category": "opening", "text": "Проверить остатки сухих ингредиентов (09:00)"},
    {"category": "opening", "text": "Проверить заполненность витрины и приготовить сэндвичи, салаты и т.д. (09:30)"},
    {"category": "daytime", "text": "Проверить порядок в холодильниках (11:00)"},
    {"category": "daytime", "text": "Написать заявки на закупку (12:00)"},
    {"category": "closing", "text": "Проверить витрину, списать просрочку"},
    {"category": "closing", "text": "Подготовить витрину к следующему дню"},
    {"category": "closing", "text": "Проверить заготовки и сроки"},
    {"category": "closing", "text": "Навести порядок на рабочем месте, убрать мусор"},
    {"category": "closing", "text": "Передать информацию по смене"},
]

# Недельные задачи (будут добавлены как отдельная категория "weekly")
BAR_WEEKLY_ITEMS = {
    0: "Навести порядок на баре, почистить кофемолку (пн)",
    1: "Оптимизировать пространство на складе и в кассовой зоне (вт)",
    2: "Почистить кофемолку, замочить термосы, собрать тряпки (ср)",
    3: "Убрать витрину, протереть зеркала (чт)",
    4: "Отодвинуть кофемолку и холодильники, убрать за ними (пт)",
    5: "Почистить кофемолку, замочить термосы, собрать тряпки (сб)",
    6: "Почистить стимеры и дисперсионные диски кофемашины (вс)",
}

KITCHEN_WEEKLY_ITEMS = {
    0: "Проверить окрошку и овсянку с бастурмой (пн)",
    1: "Навести порядок на кухонном складе (вт)",
    2: "Генеральная уборка конвекционной печи, проверить заготовки (ср)",
    3: "Уборка холодильников (чт)",
    4: "Проверить окрошку и овсянку с бастурмой (пт)",
    5: "Генеральная уборка вытяжки (сб)",
    6: "Уборка полок под печью и из-под сковородок (вс)",
}

# Читаемые названия категорий
CATEGORY_NAMES = {
    "opening": "☀️ Открытие",
    "daytime": "📅 В течение дня",
    "closing": "🌙 Закрытие",
    "weekly": "📆 Недельная задача",
}

def get_daily_items(location):
    if location == 'bar':
        return BAR_DAILY_ITEMS
    elif location == 'kitchen':
        return KITCHEN_DAILY_ITEMS
    return []

def get_weekly_item(location, day_of_week):
    if location == 'bar':
        return BAR_WEEKLY_ITEMS.get(day_of_week)
    elif location == 'kitchen':
        return KITCHEN_WEEKLY_ITEMS.get(day_of_week)
    return None