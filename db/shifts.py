from . import get_connection
from utils.time_utils import now_msk, today_msk_str, time_msk_str, yesterday_msk_str


def _auto_close_outdated_shifts(conn):
    today = today_msk_str()
    conn.execute("UPDATE shifts SET active = 0 WHERE active = 1 AND date < ?", (today,))


# ============================================================
# ТИПЫ СМЕН
# ============================================================
def import_shift_types():
    """Создаёт типы смен при первом запуске с правильными длительностями."""
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM shift_types").fetchone()[0]
        if count > 0:
            return

        shift_types = [
            # ---------- БАР ----------
            {
                "location": "bar",
                "name": "Утро (будни)",
                "start_time": "07:00",
                "duration": 540,   # 9 часов (до 16:00)
                "days": "mon,tue,wed,thu,fri"
            },
            {
                "location": "bar",
                "name": "Утро (выходные)",
                "start_time": "07:00",
                "duration": 420,   # 7 часов (до 14:00)
                "days": "sat,sun"
            },
            {
                "location": "bar",
                "name": "День",
                "start_time": "10:00",
                "duration": 780,   # 13 часов (до 23:00)
                "days": "all"
            },
            {
                "location": "bar",
                "name": "Вечер",
                "start_time": "15:00",
                "duration": 480,   # 8 часов (до 23:00)
                "days": "all"
            },

            # ---------- КУХНЯ ----------
            {
                "location": "kitchen",
                "name": "Ранняя (будни)",
                "start_time": "07:00",
                "duration": 540,   # 9 часов (до 16:00)
                "days": "mon,tue,wed,thu,fri"
            },
            {
                "location": "kitchen",
                "name": "Ранняя (выходные)",
                "start_time": "08:00",
                "duration": 720,   # 12 часов (до 20:00)
                "days": "sat,sun"
            },
            {
                "location": "kitchen",
                "name": "Поздняя",
                "start_time": "09:00",
                "duration": 750,   # 12.5 часов (до 21:30)
                "days": "all"
            },
        ]

        for i, st in enumerate(shift_types):
            conn.execute(
                """
                INSERT INTO shift_types (location, name, start_time, duration, days, sort_order)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (st["location"], st["name"], st["start_time"], st["duration"], st["days"], i)
            )
        conn.commit()


def get_shift_types_for_location(location: str, weekday: int) -> list[dict]:
    """
    Возвращает доступные типы смен для локации и дня недели.
    weekday: 0-6 (пн=0, вс=6)
    """
    weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    day_short = weekdays[weekday]

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM shift_types
            WHERE location = ?
              AND (days = 'all' OR days LIKE ? OR days LIKE ? OR days LIKE ?)
            ORDER BY sort_order
            """,
            (location, f"%{day_short}%", f"{day_short},%", f"%,{day_short}%")
        ).fetchall()
        return [dict(row) for row in rows]


def get_shift_type(shift_type_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM shift_types WHERE id = ?", (shift_type_id,)).fetchone()
        return dict(row) if row else None


def get_earliest_shift_type_id(location: str, weekday: int) -> int | None:
    """
    Возвращает ID типа смены с самым ранним start_time для локации и дня недели.
    """
    weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    day_short = weekdays[weekday]
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id
            FROM shift_types
            WHERE location = ?
              AND (days = 'all' OR days LIKE ? OR days LIKE ? OR days LIKE ?)
            ORDER BY start_time ASC
            LIMIT 1
            """,
            (location, f"%{day_short}%", f"{day_short},%", f"%,{day_short}%")
        ).fetchone()
        return row["id"] if row else None


# ============================================================
# УПРАВЛЕНИЕ СМЕНАМИ
# ============================================================
def start_shift(user_id: int, shift_type_id: int):
    """
    Начинает смену с указанным типом.
    shift_type_id должен существовать в shift_types.
    """
    shift_type = get_shift_type(shift_type_id)
    if not shift_type:
        raise ValueError("Неверный тип смены")

    with get_connection() as conn:
        _auto_close_outdated_shifts(conn)
        # Закрываем все активные смены пользователя
        conn.execute("UPDATE shifts SET active = 0 WHERE user_id = ? AND active = 1", (user_id,))

        # Вставляем новую смену
        conn.execute(
            """
            INSERT INTO shifts (user_id, shift_type_id, date, start_time, active)
            VALUES (?, ?, ?, ?, 1)
            """,
            (user_id, shift_type_id, today_msk_str(), time_msk_str())
        )
        conn.commit()


def get_active_shift(user_id: int) -> dict | None:
    """Возвращает активную смену (с полной информацией о типе)."""
    with get_connection() as conn:
        _auto_close_outdated_shifts(conn)
        row = conn.execute(
            """
            SELECT s.*,
                   st.location,
                   st.name AS shift_name,
                   st.start_time AS planned_start,
                   st.duration AS shift_duration
            FROM shifts s
            LEFT JOIN shift_types st ON s.shift_type_id = st.id
            WHERE s.user_id = ? AND s.active = 1 AND s.date = ?
            """,
            (user_id, today_msk_str())
        ).fetchone()
        return dict(row) if row else None


def end_shift(user_id: int):
    with get_connection() as conn:
        conn.execute("UPDATE shifts SET active = 0 WHERE user_id = ? AND active = 1", (user_id,))
        conn.commit()


def get_shifts_for_date(date: str) -> list[dict]:
    """Возвращает все смены за дату с информацией о типе и пользователе."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT s.*,
                   u.tg_id, u.first_name, u.last_name, u.full_name,
                   st.name AS shift_name,
                   st.location,
                   st.start_time AS planned_start,
                   st.duration AS shift_duration
            FROM shifts s
            JOIN users u ON s.user_id = u.tg_id
            LEFT JOIN shift_types st ON s.shift_type_id = st.id
            WHERE s.date = ?
            ORDER BY s.start_time
            """,
            (date,)
        ).fetchall()
        return [dict(row) for row in rows]


def get_shift_for_date(user_id: int, date: str) -> dict | None:
    """Возвращает смену пользователя за конкретную дату (с типом)."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT s.*,
                   st.location,
                   st.name AS shift_name,
                   st.start_time AS planned_start,
                   st.duration AS shift_duration
            FROM shifts s
            LEFT JOIN shift_types st ON s.shift_type_id = st.id
            WHERE s.user_id = ? AND s.date = ?
            ORDER BY s.id DESC LIMIT 1
            """,
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


# ============================================================
# ОТЧЁТЫ ПО СМЕНАМ
# ============================================================

def get_report(date_str: str, report_type: str) -> dict | None:
    """Возвращает отчёт (полный текст и parsed_data) по дате и типу."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, date, report_type, author_id, full_text, parsed_data, created_at, updated_at
            FROM shift_reports
            WHERE date = ? AND report_type = ?
            """,
            (date_str, report_type),
        ).fetchone()
    return dict(row) if row else None


def get_previous_report_of_type(date_str: str, report_type: str) -> dict | None:
    """Находит последний сохранённый отчёт указанного типа СТРОГО ДО указанной даты."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, date, report_type, author_id, full_text, parsed_data, created_at, updated_at
            FROM shift_reports
            WHERE report_type = ? AND date < ?
            ORDER BY date DESC, id DESC
            LIMIT 1
            """,
            (report_type, date_str),
        ).fetchone()
    return dict(row) if row else None


def get_last_closing_report() -> str | None:
    """Возвращает полный текст последнего отчёта закрытия (за вчера или самый свежий до сегодня)."""
    yesterday = yesterday_msk_str()
    report = get_report(yesterday, "closing")
    if report:
        return report.get("full_text")
    # Если за вчера нет, берём самый свежий до сегодня
    latest = get_previous_report_of_type(today_msk_str(), "closing")
    if latest:
        return latest.get("full_text")
    return None


# ============================================================
# НАПОМИНАНИЯ ДЛЯ ПЕРВОЙ СМЕНЫ (с учётом времени)
# ============================================================

def mark_opening_reminder_sent(location: str, date: str, shift_start_time: str) -> None:
    """Сохраняет факт отправки напоминания для конкретного времени смены в локации в указанную дату."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO opening_reminders_sent (location, date, shift_start_time, sent_at)
            VALUES (?, ?, ?, ?)
            """,
            (location, date, shift_start_time, now_msk().isoformat())
        )
        conn.commit()


def is_opening_reminder_sent(location: str, date: str, shift_start_time: str) -> bool:
    """Проверяет, отправлялось ли уже напоминание для данного времени смены в локации в эту дату."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM opening_reminders_sent WHERE location = ? AND date = ? AND shift_start_time = ?",
            (location, date, shift_start_time)
        ).fetchone()
        return row is not None