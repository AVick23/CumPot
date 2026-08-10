from db.shifts import start_shift, get_active_shift, end_shift
from datetime import datetime
from .constants import get_daily_items, get_weekly_item

def mark_shift(user_id, location):
    start_shift(user_id, location)

def get_current_shift(user_id):
    return get_active_shift(user_id)

def end_current_shift(user_id):
    end_shift(user_id)

def get_checklist_items(user_id, context):
    """Возвращает список всех пунктов (ежедневные + недельный) с флагом completed"""
    shift = get_active_shift(user_id)
    if not shift:
        return None
    location = shift['location']
    day_of_week = datetime.now().weekday()

    items = []
    # Ежедневные
    daily = get_daily_items(location)
    for item in daily:
        items.append({
            'id': None,  # временно
            'category': item['category'],
            'text': item['text'],
            'completed': False,
        })
    # Недельная задача
    weekly_text = get_weekly_item(location, day_of_week)
    if weekly_text:
        items.append({
            'id': None,
            'category': 'weekly',
            'text': weekly_text,
            'completed': False,
        })

    # Загружаем прогресс из context.user_data
    date = datetime.now().strftime("%Y-%m-%d")
    key = f"progress_{user_id}_{date}"
    progress = context.user_data.get(key, {})
    for idx, item in enumerate(items):
        if str(idx) in progress:
            item['completed'] = progress[str(idx)]
    return items

def get_items_by_category(user_id, context, category):
    """Возвращает пункты только для указанной категории"""
    all_items = get_checklist_items(user_id, context)
    if not all_items:
        return None
    return [item for item in all_items if item['category'] == category]

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
    # Прогресс по категориям
    categories = {}
    for item in items:
        cat = item['category']
        if cat not in categories:
            categories[cat] = {'total': 0, 'done': 0}
        categories[cat]['total'] += 1
        if item['completed']:
            categories[cat]['done'] += 1
    return done, total, items, categories