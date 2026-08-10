from db.shifts import get_shifts_for_date, get_shifts_for_month
from db.checklist import get_items_for_location_and_day, get_progress_for_user_date
from db.users import get_user
from datetime import datetime, timedelta

def get_today_shifts():
    date = datetime.now().strftime("%Y-%m-%d")
    return get_shifts_for_date(date)

def get_all_users():
    from db import get_connection
    with get_connection() as conn:
        rows = conn.execute("SELECT tg_id, first_name, last_name FROM users WHERE is_admin = 0").fetchall()
        return [dict(row) for row in rows]

def get_employee_progress(employee_id, date_str):
    """Возвращает прогресс сотрудника за конкретную дату"""
    from db.shifts import get_active_shift, get_shift_for_date
    # Получаем смену за эту дату
    shift = get_shift_for_date(employee_id, date_str)
    if not shift:
        return None, None
    location = shift['location']
    day_of_week = datetime.strptime(date_str, "%Y-%m-%d").weekday()
    items = get_items_for_location_and_day(location, day_of_week)
    if not items:
        return [], {}
    progress = get_progress_for_user_date(employee_id, date_str)
    progress_dict = {p['item_id']: p['completed'] for p in progress}
    # Добавляем статус выполнения
    for item in items:
        item['completed'] = progress_dict.get(item['id'], 0) == 1
    return items, progress_dict

def get_employee_shift_days(employee_id, year, month):
    """Возвращает список дней месяца, когда сотрудник был на смене (активные смены)"""
    from db import get_connection
    start_date = f"{year}-{month:02d}-01"
    # Определяем последний день месяца
    if month == 12:
        end_date = f"{year+1}-01-01"
    else:
        end_date = f"{year}-{month+1:02d}-01"
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT DISTINCT date FROM shifts
            WHERE user_id = ? AND active = 1 AND date >= ? AND date < ?
        """, (employee_id, start_date, end_date)).fetchall()
        return [dict(row)['date'] for row in rows]

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

def save_new_item(item_type, location, category, day_of_week, text):
    from db.checklist import add_checklist_item
    add_checklist_item(item_type, location, category, day_of_week, text)

def update_item(item_id, new_text):
    from db.checklist import update_checklist_item
    update_checklist_item(item_id, new_text)