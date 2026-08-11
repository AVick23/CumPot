from . import get_connection
from utils.time_utils import now_msk, today_msk_str, time_msk_str


def _auto_close_outdated_shifts(conn):
    """Автоматически закрывает смены, открытые НЕ сегодня по МСК."""
    today = today_msk_str()
    conn.execute(
        "UPDATE shifts SET active = 0 WHERE active = 1 AND date < ?",
        (today,)
    )


def start_shift(user_id: int, location: str):
    """Создаёт новую смену. Старые просроченные закрываются автоматически."""
    with get_connection() as conn:
        _auto_close_outdated_shifts(conn)

        # Закрываем текущую активную смену пользователя (если есть)
        conn.execute(
            "UPDATE shifts SET active = 0 WHERE user_id = ? AND active = 1",
            (user_id,)
        )

        conn.execute(
            """
            INSERT INTO shifts (user_id, date, location, start_time, active)
            VALUES (?, ?, ?, ?, 1)
            """,
            (user_id, today_msk_str(), location, time_msk_str())
        )
        conn.commit()


def get_active_shift(user_id: int) -> dict | None:
    """Возвращает активную смену ТОЛЬКО если она открыта сегодня по МСК."""
    with get_connection() as conn:
        _auto_close_outdated_shifts(conn)

        row = conn.execute(
            "SELECT * FROM shifts WHERE user_id = ? AND active = 1 AND date = ?",
            (user_id, today_msk_str())
        ).fetchone()
        return dict(row) if row else None


def end_shift(user_id: int):
    """Ручное завершение активной смены."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE shifts SET active = 0 WHERE user_id = ? AND active = 1",
            (user_id,)
        )
        conn.commit()


def get_shifts_for_date(date: str) -> list[dict]:
    """Все смены за конкретную дату (для админа)."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT s.*, u.first_name, u.last_name, u.full_name
            FROM shifts s
            JOIN users u ON s.user_id = u.tg_id
            WHERE s.date = ?
            ORDER BY s.start_time
            """,
            (date,)
        ).fetchall()
        return [dict(row) for row in rows]


def get_shift_for_date(user_id: int, date: str) -> dict | None:
    """Смена пользователя за конкретную дату (любая, не только активная)."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM shifts WHERE user_id = ? AND date = ?",
            (user_id, date)
        ).fetchone()
        return dict(row) if row else None


def get_shifts_for_month(user_id: int, year: int, month: int) -> list[str]:
    """Список дат за месяц, где были смены."""
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT date FROM shifts WHERE user_id = ? AND date >= ? AND date < ?",
            (user_id, start_date, end_date)
        ).fetchall()
        return [row['date'] for row in rows]