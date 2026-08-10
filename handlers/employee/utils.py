from db.shifts import start_shift, get_active_shift, end_shift
from datetime import datetime
from .constant import get_daily_items, get_weekly_items

# ------------------------------------------------------------
# Функции работы со сменами
# ------------------------------------------------------------
def mark_shift(user_id, location):
    start_shift(user_id, location)

def get_current_shift(user_id):
    return get_active_shift(user_id)

def end_current_shift(user_id):
    end_shift(user_id)

# ------------------------------------------------------------
# Функции получения чек-листов из констант с хранением прогресса в памяти
# ------------------------------------------------------------
def get_checklist_items(user_id, context):
    shift = get_active_shift(user_id)
    if not shift:
        return None
    location = shift['location']
    day_of_week = datetime.now().weekday()  # 0-6

    # Собираем ежедневные пункты
    daily = get_daily_items(location)
    # Добавляем недельный пункт, если есть
    weekly_text = get_weekly_items(location, day_of_week)
    items = []
    for item in daily:
        items.append({
            'id': None,  # временно без id, используем индекс
            'category': item['category'],
            'text': item['text'],
            'completed': False,
            'completed_at': None,
        })
    if weekly_text:
        items.append({
            'id': None,
            'category': 'недельная',
            'text': weekly_text,
            'completed': False,
            'completed_at': None,
        })

    # Загружаем прогресс из context.user_data
    date = datetime.now().strftime("%Y-%m-%d")
    key = f"progress_{user_id}_{date}"
    progress_data = context.user_data.get(key, {})
    # progress_data - словарь {индекс: True/False}
    for idx, item in enumerate(items):
        if str(idx) in progress_data:
            item['completed'] = progress_data[str(idx)]
        else:
            item['completed'] = False
    return items

def mark_item_done(user_id, item_id, context):
    date = datetime.now().strftime("%Y-%m-%d")
    key = f"progress_{user_id}_{date}"
    progress = context.user_data.get(key, {})
    progress[str(item_id)] = True
    context.user_data[key] = progress

def mark_item_undone(user_id, item_id, context):
    date = datetime.now().strftime("%Y-%m-%d")
    key = f"progress_{user_id}_{date}"
    progress = context.user_data.get(key, {})
    progress[str(item_id)] = False
    context.user_data[key] = progress

def get_user_progress_summary(user_id, context):
    items = get_checklist_items(user_id, context)
    if not items:
        return None, None, None
    total = len(items)
    done = sum(1 for i in items if i['completed'])
    return done, total, items