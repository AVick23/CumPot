from . import get_connection
from utils.time_utils import today_msk_str, time_msk_str, now_msk
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# СТАРТОВЫЕ ЧЕК-ЛИСТЫ (импорт при создании БД)
# ------------------------------------------------------------
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


def _clean(item: dict, key: str) -> str:
    return item.get(key, item.get(f"{key} ", "")).strip()


def import_checklist_items():
    """Импортирует стартовые чек-листы, если таблица пуста."""
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM checklist_items").fetchone()[0]
        if count > 0:
            logger.info(f"Чек-листы уже импортированы ({count} записей). Пропуск.")
            return

        logger.info("Начинаю импорт стартовых чек-листов...")
        for item in BAR_DAILY_ITEMS:
            conn.execute(
                """
                INSERT INTO checklist_items
                (type, location, category, day_of_week, days_of_week, sort_order, text, requires_photo, requires_notification, notification_time, is_recurring)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ('daily', 'bar', _clean(item, 'category'), None, None, 0, _clean(item, 'text'), 0, 0, None, 1)
            )
        for item in KITCHEN_DAILY_ITEMS:
            conn.execute(
                """
                INSERT INTO checklist_items
                (type, location, category, day_of_week, days_of_week, sort_order, text, requires_photo, requires_notification, notification_time, is_recurring)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ('daily', 'kitchen', _clean(item, 'category'), None, None, 0, _clean(item, 'text'), 0, 0, None, 1)
            )
        for day, text in BAR_WEEKLY_ITEMS.items():
            conn.execute(
                """
                INSERT INTO checklist_items
                (type, location, category, day_of_week, days_of_week, sort_order, text, requires_photo, requires_notification, notification_time, is_recurring)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ('weekly', 'bar', 'weekly', int(day), str(day), 0, text.strip(), 0, 0, None, 1)
            )
        for day, text in KITCHEN_WEEKLY_ITEMS.items():
            conn.execute(
                """
                INSERT INTO checklist_items
                (type, location, category, day_of_week, days_of_week, sort_order, text, requires_photo, requires_notification, notification_time, is_recurring)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ('weekly', 'kitchen', 'weekly', int(day), str(day), 0, text.strip(), 0, 0, None, 1)
            )
        conn.commit()
        logger.info("Импорт чек-листов успешно завершён.")


def get_items_for_location_and_day(location: str, date: str) -> list[dict]:
    """
    Возвращает все задачи для локации и даты:
    - daily (всегда)
    - weekly, если день недели присутствует в days_of_week (или, если days_of_week NULL, используется day_of_week)
    - once (одноразовые) с due_date == date
    Учитывает поля requires_photo, requires_notification, notification_time.
    """
    if date == today_msk_str():
        day_of_week = now_msk().weekday()
    else:
        day_of_week = datetime.strptime(date, "%Y-%m-%d").weekday()

    day_str = str(day_of_week)

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM checklist_items
            WHERE location = ?
              AND (
                  type = 'daily'
                  OR (type = 'weekly' AND (
                      days_of_week LIKE ? OR days_of_week LIKE ? OR days_of_week LIKE ?
                      OR (day_of_week = ? AND days_of_week IS NULL)
                  ))
                  OR (type = 'once' AND due_date = ?)
              )
            ORDER BY
                CASE category
                    WHEN 'opening' THEN 1
                    WHEN 'daytime' THEN 2
                    WHEN 'closing' THEN 3
                    WHEN 'weekly' THEN 4
                    ELSE 5
                END,
                sort_order ASC, id ASC
            """,
            (location,
             f"%{day_str}%", f"{day_str},%", f"%,{day_str}%",  # для days_of_week
             day_of_week,  # для старых записей
             date)
        ).fetchall()
        return [dict(row) for row in rows]


# ------------------------------------------------------------
# ОБЩИЙ ПРОГРЕСС (для локации и даты)
# ------------------------------------------------------------
def save_shared_progress(location: str, date: str, item_id: int, completed: bool = True, completed_by: int = None):
    completed_at = time_msk_str() if completed else None
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM checklist_shared_progress WHERE location = ? AND date = ? AND item_id = ?",
            (location, date, item_id)
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE checklist_shared_progress
                SET completed = ?, completed_at = ?, completed_by = ?
                WHERE id = ?
                """,
                (1 if completed else 0, completed_at, completed_by, existing["id"])
            )
        else:
            conn.execute(
                """
                INSERT INTO checklist_shared_progress
                (location, date, item_id, completed, completed_at, completed_by)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (location, date, item_id, 1 if completed else 0, completed_at, completed_by)
            )
        conn.commit()


def get_shared_progress(location: str, date: str) -> dict[int, dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT item_id, completed, completed_at, completed_by,
                   photo_file_id, photo_channel_message_id,
                   photo_file_ids, photo_channel_message_ids
            FROM checklist_shared_progress
            WHERE location = ? AND date = ?
            """,
            (location, date)
        ).fetchall()
        return {row["item_id"]: dict(row) for row in rows}


def save_shared_photo(location: str, date: str, item_id: int, file_id: str, channel_message_id: int, completed_by: int = None):
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM checklist_shared_progress WHERE location = ? AND date = ? AND item_id = ?",
            (location, date, item_id)
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE checklist_shared_progress
                SET photo_file_id = ?, photo_channel_message_id = ?
                WHERE id = ?
                """,
                (file_id, channel_message_id, existing["id"])
            )
        else:
            conn.execute(
                """
                INSERT INTO checklist_shared_progress
                (location, date, item_id, completed, completed_at, completed_by, photo_file_id, photo_channel_message_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (location, date, item_id, 0, None, completed_by, file_id, channel_message_id)
            )
        conn.commit()


def delete_shared_progress(location: str, date: str, item_id: int):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM checklist_shared_progress WHERE location = ? AND date = ? AND item_id = ?",
            (location, date, item_id)
        )
        conn.commit()


# ------------------------------------------------------------
# РЕДАКТОР ЧЕК-ЛИСТОВ (обновлённые функции)
# ------------------------------------------------------------
def get_all_items() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM checklist_items ORDER BY location, category, sort_order, id").fetchall()
        return [dict(row) for row in rows]


def get_item_by_id(item_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM checklist_items WHERE id = ?", (item_id,)).fetchone()
        return dict(row) if row else None


def add_checklist_item(
    item_type: str,
    location: str,
    category: str,
    day_of_week: int | None,
    text: str,
    requires_photo: bool = False,
    requires_notification: bool = False,
    notification_time: str | None = None,
    due_date: str | None = None,
    is_recurring: bool = True,
    days_of_week: str | None = None
):
    """
    Добавляет новый пункт чек-листа.
    Для type='once' нужно указать due_date, is_recurring=False.
    notification_time — строка HH:MM, обязательна, если requires_notification=True.
    days_of_week — строка "0,1,2" для weekly (может быть None, тогда используется day_of_week).
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT MAX(sort_order) as max_order FROM checklist_items WHERE location = ? AND category = ?",
            (location, category)
        ).fetchone()
        order = (row['max_order'] or 0) + 1

        if item_type == 'once':
            is_recurring = False
            day_of_week = None
            days_of_week = None

        if requires_notification and not notification_time:
            notification_time = None

        conn.execute(
            """
            INSERT INTO checklist_items
            (type, location, category, day_of_week, days_of_week, sort_order, text,
             requires_photo, requires_notification, notification_time, due_date, is_recurring)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (item_type, location, category, day_of_week, days_of_week, order, text.strip(),
             1 if requires_photo else 0,
             1 if requires_notification else 0,
             notification_time,
             due_date,
             1 if is_recurring else 0)
        )
        conn.commit()


def update_checklist_item(item_id: int, **kwargs):
    """
    Обновляет любые поля пункта чек-листа.
    Допустимые ключи: text, requires_photo, requires_notification, notification_time,
                       due_date, is_recurring, category, location, day_of_week, type, days_of_week.
    """
    allowed_fields = {
        'text', 'requires_photo', 'requires_notification', 'notification_time',
        'due_date', 'is_recurring', 'category', 'location', 'day_of_week', 'type', 'days_of_week'
    }
    updates = []
    params = []
    for key, value in kwargs.items():
        if key in allowed_fields:
            updates.append(f"{key} = ?")
            params.append(value)
    if not updates:
        return
    params.append(item_id)
    with get_connection() as conn:
        conn.execute(f"UPDATE checklist_items SET {', '.join(updates)} WHERE id = ?", tuple(params))
        conn.commit()


def delete_checklist_item(item_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM checklist_shared_progress WHERE item_id = ?", (item_id,))
        conn.execute("DELETE FROM checklist_notifications_sent WHERE item_id = ?", (item_id,))
        conn.execute("DELETE FROM checklist_items WHERE id = ?", (item_id,))
        conn.commit()


# ------------------------------------------------------------
# УВЕДОМЛЕНИЯ
# ------------------------------------------------------------
def mark_notification_sent(item_id: int, date: str):
    with get_connection() as conn:
        sent_at = time_msk_str()
        conn.execute(
            """
            INSERT OR REPLACE INTO checklist_notifications_sent (item_id, date, sent_at)
            VALUES (?, ?, ?)
            """,
            (item_id, date, sent_at)
        )
        conn.commit()


def is_notification_sent(item_id: int, date: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM checklist_notifications_sent WHERE item_id = ? AND date = ?",
            (item_id, date)
        ).fetchone()
        return row is not None


def get_items_requiring_notification(location: str, date: str) -> list[dict]:
    items = get_items_for_location_and_day(location, date)
    result = []
    for item in items:
        if (item.get("requires_notification") and
            item.get("notification_time") is not None and
            not is_notification_sent(item["id"], date)):
            result.append(item)
    return result