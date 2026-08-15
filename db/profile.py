from . import get_connection
from utils.time_utils import now_msk, today_msk_str
import logging

logger = logging.getLogger(__name__)


# =========================================================
# ЛИЧНЫЕ ДАННЫЕ ПОЛЬЗОВАТЕЛЯ
# =========================================================

def update_user_profile(tg_id: int, **kwargs):
    """
    Обновляет личные данные пользователя.
    Допустимые ключи: phone, birthday, address, responsibilities, full_name, position.
    """
    allowed = {"phone", "birthday", "address", "responsibilities", "full_name", "position"}
    updates = []
    params = []
    for key, value in kwargs.items():
        if key in allowed and value is not None:
            updates.append(f"{key} = ?")
            params.append(value.strip() if isinstance(value, str) else value)
    if not updates:
        return
    params.append(tg_id)
    with get_connection() as conn:
        conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE tg_id = ?", tuple(params))
        conn.commit()


def get_user_profile(tg_id: int) -> dict | None:
    """Возвращает все данные пользователя, включая личные."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT tg_id, username, first_name, last_name, full_name, position, "
            "phone, birthday, address, responsibilities, is_admin, status, admin_comment "
            "FROM users WHERE tg_id = ?",
            (tg_id,)
        ).fetchone()
        return dict(row) if row else None


# =========================================================
# УПРАВЛЕНИЕ СОТРУДНИКАМИ
# =========================================================

def update_employee_status(tg_id: int, status: str) -> None:
    """Обновляет статус сотрудника (стажёр/сотрудник)."""
    with get_connection() as conn:
        conn.execute("UPDATE users SET status = ? WHERE tg_id = ?", (status, tg_id))
        conn.commit()


def update_employee_comment(tg_id: int, comment: str | None) -> None:
    """Обновляет комментарий администратора по сотруднику."""
    with get_connection() as conn:
        conn.execute("UPDATE users SET admin_comment = ? WHERE tg_id = ?", (comment, tg_id))
        conn.commit()


def get_employee_full_info(tg_id: int) -> dict | None:
    """Возвращает полную информацию о сотруднике без ставки (только профиль)."""
    return get_user_profile(tg_id)