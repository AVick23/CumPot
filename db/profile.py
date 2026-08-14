from . import get_connection
from utils.time_utils import now_msk, today_msk_str
import json
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
# СТАВКИ (salary_rates)
# =========================================================

def set_salary_rate(user_id: int, rate: float, date_from: str, date_to: str | None = None) -> int:
    """
    Устанавливает ставку для сотрудника на указанный период.
    Если date_to не указан, считается бессрочной (до следующей ставки).
    Возвращает id записи.
    """
    now = now_msk().isoformat()
    with get_connection() as conn:
        # Закрываем предыдущую ставку, если она была открыта (date_to IS NULL)
        if date_to is None:
            # Если добавляем новую бессрочную ставку, закрываем предыдущую
            conn.execute(
                "UPDATE salary_rates SET date_to = ? WHERE user_id = ? AND date_to IS NULL",
                (date_from, user_id)
            )
        cur = conn.execute(
            """
            INSERT INTO salary_rates (user_id, rate, date_from, date_to, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, rate, date_from, date_to, now, now)
        )
        conn.commit()
        return cur.lastrowid


def get_current_salary_rate(user_id: int, date: str | None = None) -> float | None:
    """
    Возвращает ставку, действующую на указанную дату (по умолчанию сегодня).
    """
    if date is None:
        date = today_msk_str()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT rate FROM salary_rates
            WHERE user_id = ? AND date_from <= ? AND (date_to IS NULL OR date_to >= ?)
            ORDER BY date_from DESC
            LIMIT 1
            """,
            (user_id, date, date)
        ).fetchone()
        return row["rate"] if row else None


def get_salary_history(user_id: int) -> list[dict]:
    """Возвращает все записи ставок для пользователя."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, rate, date_from, date_to, created_at, updated_at
            FROM salary_rates
            WHERE user_id = ?
            ORDER BY date_from DESC
            """,
            (user_id,)
        ).fetchall()
        return [dict(row) for row in rows]


# =========================================================
# ТАКСИ (taxi_expenses)
# =========================================================

def add_taxi_expense(
    user_id: int,
    date: str,
    amount: float,
    photo_file_ids: list[str] | None = None,
    photo_channel_message_ids: list[int] | None = None
) -> int:
    """
    Добавляет запись о расходах на такси.
    photo_file_ids и photo_channel_message_ids должны быть списками (или None).
    """
    now = now_msk().isoformat()
    photo_file_ids_json = json.dumps(photo_file_ids) if photo_file_ids else None
    photo_channel_message_ids_json = json.dumps(photo_channel_message_ids) if photo_channel_message_ids else None

    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO taxi_expenses (
                user_id, date, amount, photo_file_ids, photo_channel_message_ids,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, date, amount, photo_file_ids_json, photo_channel_message_ids_json, now, now)
        )
        conn.commit()
        return cur.lastrowid


def get_taxi_expenses(
    user_id: int,
    date_from: str | None = None,
    date_to: str | None = None
) -> list[dict]:
    """
    Возвращает записи такси для пользователя за указанный период.
    Если даты не указаны – все записи.
    """
    sql = "SELECT id, user_id, date, amount, photo_file_ids, photo_channel_message_ids, created_at, updated_at FROM taxi_expenses WHERE user_id = ?"
    params = [user_id]
    if date_from:
        sql += " AND date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND date <= ?"
        params.append(date_to)
    sql += " ORDER BY date DESC"
    with get_connection() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            # Преобразуем JSON обратно в списки, если они были
            if d.get("photo_file_ids"):
                try:
                    d["photo_file_ids"] = json.loads(d["photo_file_ids"])
                except:
                    d["photo_file_ids"] = None
            if d.get("photo_channel_message_ids"):
                try:
                    d["photo_channel_message_ids"] = json.loads(d["photo_channel_message_ids"])
                except:
                    d["photo_channel_message_ids"] = None
            result.append(d)
        return result


def get_taxi_summary(user_id: int, date_from: str, date_to: str) -> dict:
    """
    Возвращает сумму расходов на такси за период и количество записей.
    """
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total
            FROM taxi_expenses
            WHERE user_id = ? AND date >= ? AND date <= ?
            """,
            (user_id, date_from, date_to)
        ).fetchone()
        return dict(row)


# =========================================================
# УПРАВЛЕНИЕ СОТРУДНИКАМИ (НОВЫЕ ФУНКЦИИ)
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
    """Возвращает полную информацию о сотруднике с текущей ставкой."""
    user = get_user_profile(tg_id)
    if user:
        user["current_rate"] = get_current_salary_rate(tg_id) or 0.0
    return user