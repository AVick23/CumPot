from . import get_connection
from config import ADMIN_IDS

def save_user(tg_id, username, first_name, last_name):
    """Сохраняет или обновляет пользователя, проставляет админа"""
    is_admin = 1 if tg_id in ADMIN_IDS else 0
    with get_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO users (tg_id, username, first_name, last_name, is_admin)
            VALUES (?, ?, ?, ?, ?)
        """, (tg_id, username, first_name, last_name, is_admin))
        conn.commit()

def get_user(tg_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
        return dict(row) if row else None