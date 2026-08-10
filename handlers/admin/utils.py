from db.shifts import get_shifts_for_date
from db.checklist import get_items_for_location_and_day, get_progress_for_user_date
from db.users import get_user
from datetime import datetime
from .constant import *

def get_today_shifts():
    date = datetime.now().strftime("%Y-%m-%d")
    return get_shifts_for_date(date)

def get_all_users():
    """Возвращает всех сотрудников (не админов) для выбора"""
    from db import get_connection
    with get_connection() as conn:
        rows = conn.execute("SELECT tg_id, first_name, last_name FROM users WHERE is_admin = 0").fetchall()
        return [dict(row) for row in rows]

def get_employee_progress(employee_id, date=None):
    """Возвращает прогресс сотрудника по его активной смене"""
    from db.shifts import get_active_shift
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    shift = get_active_shift(employee_id)
    if not shift:
        return None, None
    location = shift['location']
    day_of_week = datetime.now().weekday()
    items = get_items_for_location_and_day(location, day_of_week)
    if not items:
        return [], {}
    progress = get_progress_for_user_date(employee_id, date)
    progress_dict = {p['item_id']: p['completed'] for p in progress}
    return items, progress_dict

def get_all_checklist_items():
    from db import get_connection
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM checklist_items ORDER BY location, category, sort_order").fetchall()
        return [dict(row) for row in rows]

def delete_checklist_item(item_id):
    from db import get_connection
    with get_connection() as conn:
        conn.execute("DELETE FROM checklist_items WHERE id = ?", (item_id,))
        conn.commit()