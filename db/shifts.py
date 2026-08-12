from . import get_connection
from utils.time_utils import now_msk, today_msk_str, time_msk_str


def _auto_close_outdated_shifts(conn):
    today = today_msk_str()
    conn.execute("UPDATE shifts SET active = 0 WHERE active = 1 AND date < ?", (today,))


def start_shift(user_id: int, location: str):
    with get_connection() as conn:
        _auto_close_outdated_shifts(conn)
        conn.execute("UPDATE shifts SET active = 0 WHERE user_id = ? AND active = 1", (user_id,))
        conn.execute(
            """
            INSERT INTO shifts (user_id, date, location, start_time, active)
            VALUES (?, ?, ?, ?, 1)
            """,
            (user_id, today_msk_str(), location, time_msk_str())
        )
        conn.commit()


def get_active_shift(user_id: int) -> dict | None:
    with get_connection() as conn:
        _auto_close_outdated_shifts(conn)
        row = conn.execute(
            "SELECT * FROM shifts WHERE user_id = ? AND active = 1 AND date = ?",
            (user_id, today_msk_str())
        ).fetchone()
        return dict(row) if row else None


def end_shift(user_id: int):
    with get_connection() as conn:
        conn.execute("UPDATE shifts SET active = 0 WHERE user_id = ? AND active = 1", (user_id,))
        conn.commit()


def get_shifts_for_date(date: str) -> list[dict]:
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
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM shifts WHERE user_id = ? AND date = ? ORDER BY id DESC LIMIT 1",
            (user_id, date)
        ).fetchone()
        return dict(row) if row else None


def get_shifts_for_month(user_id: int, year: int, month: int) -> set[str]:
    start_date = f"{year:04d}-{month:02d}-01"
    end_date = f"{year + 1}-01-01" if month == 12 else f"{year:04d}-{month + 1:02d}-01"
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT date FROM shifts WHERE user_id = ? AND date >= ? AND date < ?",
            (user_id, start_date, end_date)
        ).fetchall()
        return {row["date"] for row in rows}