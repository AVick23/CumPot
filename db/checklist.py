from . import get_connection
from datetime import datetime

def get_items_for_location_and_day(location, day_of_week):
    """Возвращает пункты чек-листа для локации и дня недели (daily + weekly, если совпадает)"""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM checklist_items
            WHERE location = ?
            AND (type = 'daily' OR (type = 'weekly' AND day_of_week = ?))
            ORDER BY category, sort_order
        """, (location, day_of_week)).fetchall()
        return [dict(row) for row in rows]

def save_progress(user_id, item_id, completed=True):
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

def get_progress_for_user_date(user_id, date):
    """Возвращает прогресс из checklist_progress (без JOIN с checklist_items)"""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT item_id, completed, completed_at
            FROM checklist_progress
            WHERE user_id = ? AND date = ?
        """, (user_id, date)).fetchall()
        return [dict(row) for row in rows]