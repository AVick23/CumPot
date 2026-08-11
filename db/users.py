from . import get_connection
from config import ADMIN_IDS


def save_user(tg_id: int, username: str | None = None, first_name: str | None = None, last_name: str | None = None):
    """
    Создаёт пользователя, если его нет.
    Если уже есть — обновляет username/is_admin, но НЕ затирает full_name и position.
    """
    is_admin = 1 if tg_id in ADMIN_IDS else 0

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT tg_id FROM users WHERE tg_id = ?",
            (tg_id,)
        ).fetchone()

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
                INSERT INTO users (tg_id, username, first_name, last_name, full_name, position, is_admin)
                VALUES (?, ?, ?, ?, NULL, NULL, ?)
                """,
                (tg_id, username, first_name, last_name, is_admin)
            )

        conn.commit()


def get_user(tg_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE tg_id = ?",
            (tg_id,)
        ).fetchone()
        return dict(row) if row else None


def update_user_profile(
    tg_id: int,
    full_name: str | None = None,
    position: str | None = None
):
    """
    Обновляет профиль сотрудника: ФИО и позицию.
    """
    updates = []
    params = []

    if full_name is not None:
        updates.append("full_name = ?")
        params.append(full_name.strip())

    if position is not None:
        updates.append("position = ?")
        params.append(position)

    if not updates:
        return

    params.append(tg_id)

    with get_connection() as conn:
        conn.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE tg_id = ?",
            tuple(params)
        )
        conn.commit()