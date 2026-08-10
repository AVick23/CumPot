from . import get_connection
from datetime import datetime

def start_shift(user_id, location):
    """Создаёт новую смену и деактивирует предыдущие активные для этого пользователя"""
    date = datetime.now().strftime("%Y-%m-%d")
    start_time = datetime.now().strftime("%H:%M:%S")
    with get_connection() as conn:
        # Деактивируем все активные смены для пользователя (на случай, если он забыл закрыть)
        conn.execute("UPDATE shifts SET active = 0 WHERE user_id = ? AND active = 1", (user_id,))
        conn.execute("""
            INSERT INTO shifts (user_id, date, location, start_time, active)
            VALUES (?, ?, ?, ?, 1)
        """, (user_id, date, location, start_time))
        conn.commit()

def get_active_shift(user_id):
    """Возвращает активную смену пользователя или None"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM shifts WHERE user_id = ? AND active = 1",
            (user_id,)
        ).fetchone()
        return dict(row) if row else None

def end_shift(user_id):
    """Деактивирует активную смену"""
    with get_connection() as conn:
        conn.execute("UPDATE shifts SET active = 0 WHERE user_id = ? AND active = 1", (user_id,))
        conn.commit()

def get_shifts_for_date(date):
    """Возвращает все активные смены за дату (для админа)"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT s.*, u.first_name, u.last_name FROM shifts s JOIN users u ON s.user_id = u.tg_id WHERE s.date = ? AND s.active = 1",
            (date,)
        ).fetchall()
        return [dict(row) for row in rows]
    
def get_shift_for_date(user_id, date):
    """Возвращает смену пользователя за конкретную дату (активную)"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM shifts WHERE user_id = ? AND date = ? AND active = 1",
            (user_id, date)
        ).fetchone()
        return dict(row) if row else None

def get_shifts_for_month(user_id, year, month):
    """Возвращает список дат (строки) за месяц, где была активная смена"""
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year+1}-01-01"
    else:
        end_date = f"{year}-{month+1:02d}-01"
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT date FROM shifts WHERE user_id = ? AND active = 1 AND date >= ? AND date < ?",
            (user_id, start_date, end_date)
        ).fetchall()
        return [row['date'] for row in rows]