from . import get_connection
from config import ADMIN_IDS


def save_user(tg_id: int, username: str | None = None, first_name: str | None = None, last_name: str | None = None):
    is_admin = 1 if tg_id in ADMIN_IDS else 0
    with get_connection() as conn:
        existing = conn.execute("SELECT tg_id FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE users SET username = ?, is_admin = ? WHERE tg_id = ?",
                (username, is_admin, tg_id)
            )
            if first_name is not None or last_name is not None:
                conn.execute(
                    "UPDATE users SET first_name = ?, last_name = ? WHERE tg_id = ?",
                    (first_name, last_name, tg_id)
                )
        else:
            conn.execute(
                """
                INSERT INTO users (tg_id, username, first_name, last_name, full_name, position, is_admin, is_active)
                VALUES (?, ?, ?, ?, NULL, NULL, ?, 1)
                """,
                (tg_id, username, first_name, last_name, is_admin)
            )
        conn.commit()


def get_user(tg_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
        return dict(row) if row else None


def get_all_users() -> list[dict]:
    """Возвращает всех пользователей без учёта is_active (для админ-отчётов)."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY full_name, first_name").fetchall()
        return [dict(row) for row in rows]


def get_active_users() -> list[dict]:
    """Возвращает только активных сотрудников (is_active = 1)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM users WHERE is_active = 1 ORDER BY full_name, first_name"
        ).fetchall()
        return [dict(row) for row in rows]


def deactivate_user(tg_id: int) -> None:
    """Скрывает сотрудника из списка (is_active = 0), данные сохраняются."""
    with get_connection() as conn:
        conn.execute("UPDATE users SET is_active = 0 WHERE tg_id = ?", (tg_id,))
        conn.commit()


def activate_user(tg_id: int) -> None:
    """Восстанавливает сотрудника в список (is_active = 1)."""
    with get_connection() as conn:
        conn.execute("UPDATE users SET is_active = 1 WHERE tg_id = ?", (tg_id,))
        conn.commit()


def update_user_profile(tg_id: int, full_name: str | None = None, position: str | None = None):
    """
    Обновляет только ФИО и позицию (устаревшая функция, лучше использовать profile.update_user_profile).
    Оставлена для обратной совместимости.
    """
    updates = []
    params = []
    if full_name is not None:
        updates.append("full_name = ?")
        params.append(full_name.strip())
    if position is not None:
        updates.append("position = ?")
        params.append(position.strip())
    if not updates:
        return
    params.append(tg_id)
    with get_connection() as conn:
        conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE tg_id = ?", tuple(params))
        conn.commit()