from . import get_connection
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ==========================================
# ДАННЫЕ ДЛЯ ИМПОРТА (СТАРТОВЫЕ ЧЕК-ЛИСТЫ)
# ==========================================

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


# ==========================================
# ФУНКЦИИ РАБОТЫ С БД
# ==========================================

def import_checklist_items():
    """
    Импортирует стартовые чек-листы в БД.
    Выполняется только если таблица checklist_items пуста.
    """
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM checklist_items").fetchone()[0]
        if count > 0:
            logger.info(f"Чек-листы уже импортированы ({count} записей). Пропуск.")
            return

        logger.info("Начинаю импорт стартовых чек-листов...")
        
        # Импорт ежедневных задач бара
        for item in BAR_DAILY_ITEMS:
            conn.execute(
                "INSERT INTO checklist_items (type, location, category, day_of_week, sort_order, text) VALUES (?, ?, ?, ?, ?, ?)",
                ('daily', 'bar', item['category'].strip(), None, 0, item['text'].strip())
            )

        # Импорт ежедневных задач кухни
        for item in KITCHEN_DAILY_ITEMS:
            conn.execute(
                "INSERT INTO checklist_items (type, location, category, day_of_week, sort_order, text) VALUES (?, ?, ?, ?, ?, ?)",
                ('daily', 'kitchen', item['category'].strip(), None, 0, item['text'].strip())
            )

        # Импорт недельных задач бара
        for day, text in BAR_WEEKLY_ITEMS.items():
            conn.execute(
                "INSERT INTO checklist_items (type, location, category, day_of_week, sort_order, text) VALUES (?, ?, ?, ?, ?, ?)",
                ('weekly', 'bar', 'weekly', int(day), 0, text.strip())
            )

        # Импорт недельных задач кухни
        for day, text in KITCHEN_WEEKLY_ITEMS.items():
            conn.execute(
                "INSERT INTO checklist_items (type, location, category, day_of_week, sort_order, text) VALUES (?, ?, ?, ?, ?, ?)",
                ('weekly', 'kitchen', 'weekly', int(day), 0, text.strip())
            )

        conn.commit()
        logger.info("Импорт чек-листов успешно завершён.")


def get_items_for_location_and_day(location: str, day_of_week: int) -> list[dict]:
    """
    Возвращает список задач для конкретной локации и дня недели.
    Включает:
    - Все daily задачи для этой локации
    - Weekly задачи, у которых day_of_week совпадает с переданным
    """
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM checklist_items
            WHERE location = ?
              AND (
                  type = 'daily' 
                  OR (type = 'weekly' AND day_of_week = ?)
              )
            ORDER BY 
                CASE category 
                    WHEN 'opening' THEN 1 
                    WHEN 'daytime' THEN 2 
                    WHEN 'closing' THEN 3 
                    WHEN 'weekly' THEN 4 
                    ELSE 5 
                END,
                sort_order ASC,
                id ASC
        """, (location, day_of_week)).fetchall()
        
        return [dict(row) for row in rows]


def save_progress(user_id: int, item_id: int, completed: bool = True):
    """Сохраняет или обновляет прогресс выполнения задачи"""
    date = datetime.now().strftime("%Y-%m-%d")
    completed_at = datetime.now().strftime("%H:%M:%S") if completed else None
    
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM checklist_progress WHERE user_id = ? AND item_id = ? AND date = ?",
            (user_id, item_id, date)
        ).fetchone()
        
        if row:
            conn.execute(
                "UPDATE checklist_progress SET completed = ?, completed_at = ? WHERE id = ?",
                (1 if completed else 0, completed_at, row['id'])
            )
        else:
            conn.execute(
                "INSERT INTO checklist_progress (user_id, item_id, date, completed, completed_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, item_id, date, 1 if completed else 0, completed_at)
            )
        conn.commit()


def get_progress_for_user_date(user_id: int, date: str) -> list[dict]:
    """Возвращает прогресс пользователя за конкретную дату"""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT item_id, completed, completed_at
            FROM checklist_progress
            WHERE user_id = ? AND date = ?
        """, (user_id, date)).fetchall()
        return [dict(row) for row in rows]


def add_checklist_item(item_type: str, location: str, category: str, day_of_week: int | None, text: str):
    """Добавляет новый пункт в чек-лист с автоматическим sort_order"""
    with get_connection() as conn:
        # Получаем максимальный sort_order для этой локации и категории
        row = conn.execute(
            "SELECT MAX(sort_order) as max_order FROM checklist_items WHERE location = ? AND category = ?",
            (location, category)
        ).fetchone()
        order = (row['max_order'] or 0) + 1
        
        conn.execute(
            "INSERT INTO checklist_items (type, location, category, day_of_week, sort_order, text) VALUES (?, ?, ?, ?, ?, ?)",
            (item_type, location, category, day_of_week, order, text.strip())
        )
        conn.commit()


def update_checklist_item(item_id: int, new_text: str):
    """Обновляет текст существующего пункта"""
    with get_connection() as conn:
        conn.execute(
            "UPDATE checklist_items SET text = ? WHERE id = ?", 
            (new_text.strip(), item_id)
        )
        conn.commit()


def delete_checklist_item(item_id: int):
    """Удаляет пункт из чек-листа"""
    with get_connection() as conn:
        conn.execute("DELETE FROM checklist_items WHERE id = ?", (item_id,))
        conn.commit()


def get_all_items() -> list[dict]:
    """Возвращает ВСЕ пункты чек-листов (для админского редактора)"""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM checklist_items 
            ORDER BY location, category, sort_order, id
        """).fetchall()
        return [dict(row) for row in rows]