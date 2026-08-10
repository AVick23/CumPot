from db.shifts import start_shift, get_active_shift, end_shift
from db.checklist import get_items_for_location_and_day, save_progress, get_progress_for_user_date
from datetime import datetime

def mark_shift(user_id, location):
    start_shift(user_id, location)

def get_current_shift(user_id):
    return get_active_shift(user_id)

def end_current_shift(user_id):
    end_shift(user_id)

def get_checklist_items(user_id):
    # Определяем локацию пользователя (из активной смены)
    shift = get_active_shift(user_id)
    if not shift:
        return None
    location = shift['location']
    day_of_week = datetime.now().weekday()  # 0-6
    items = get_items_for_location_and_day(location, day_of_week)
    # Добавляем статус выполнения для сегодня
    date = datetime.now().strftime("%Y-%m-%d")
    progress = get_progress_for_user_date(user_id, date)
    # Сопоставляем
    progress_dict = {p['id']: p for p in progress}
    for item in items:
        if item['id'] in progress_dict:
            item['completed'] = progress_dict[item['id']]['completed'] == 1
            item['completed_at'] = progress_dict[item['id']]['completed_at']
        else:
            item['completed'] = False
            item['completed_at'] = None
    return items

def mark_item_done(user_id, item_id):
    save_progress(user_id, item_id, True)

def mark_item_undone(user_id, item_id):
    save_progress(user_id, item_id, False)

def get_user_progress_summary(user_id):
    items = get_checklist_items(user_id)
    if not items:
        return None, None
    total = len(items)
    done = sum(1 for i in items if i['completed'])
    return done, total, items