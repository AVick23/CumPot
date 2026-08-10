from db.shifts import start_shift, get_active_shift, end_shift
from db.checklist import save_progress, get_progress_for_user_date
from datetime import datetime
from .constants import get_daily_items, get_weekly_item

def mark_shift(user_id, location):
    start_shift(user_id, location)

def get_current_shift(user_id):
    return get_active_shift(user_id)

def end_current_shift(user_id):
    end_shift(user_id)

def get_checklist_items(user_id, context):
    """Возвращает список всех пунктов (ежедневные + недельный) с флагом completed из БД"""
    shift = get_active_shift(user_id)
    if not shift:
        return None
    location = shift['location']
    day_of_week = datetime.now().weekday()
    date = datetime.now().strftime("%Y-%m-%d")

    # Получаем все пункты из констант
    items = []
    daily = get_daily_items(location)
    for item in daily:
        items.append({
            'id': None,  # временно, будем использовать индекс как id
            'category': item['category'],
            'text': item['text'],
            'completed': False,
        })
    weekly_text = get_weekly_item(location, day_of_week)
    if weekly_text:
        items.append({
            'id': None,
            'category': 'weekly',
            'text': weekly_text,
            'completed': False,
        })

    # Получаем прогресс из БД
    progress_list = get_progress_for_user_date(user_id, date)
    # Превращаем в словарь для быстрого доступа по индексу (используем порядковый номер)
    progress_dict = {}
    for p in progress_list:
        # Используем индекс (порядковый номер) как ключ
        # Так как у нас нет реального item_id, мы будем хранить прогресс по индексу.
        # Для этого в БД мы будем сохранять item_id = индекс.
        progress_dict[p['item_id']] = p['completed'] == 1

    # Применяем прогресс к пунктам
    for idx, item in enumerate(items):
        if idx in progress_dict:
            item['completed'] = progress_dict[idx]

    return items

def get_items_by_category(user_id, context, category):
    all_items = get_checklist_items(user_id, context)
    if not all_items:
        return None
    return [item for item in all_items if item['category'] == category]

def mark_item_done(user_id, item_id, context):
    # item_id - это индекс (порядковый номер)
    date = datetime.now().strftime("%Y-%m-%d")
    # Сохраняем в БД с item_id = индекс
    save_progress(user_id, item_id, True)   # передаём индекс как item_id

def mark_item_undone(user_id, item_id, context):
    date = datetime.now().strftime("%Y-%m-%d")
    save_progress(user_id, item_id, False)

def get_user_progress_summary(user_id, context):
    items = get_checklist_items(user_id, context)
    if not items:
        return None, None, None
    total = len(items)
    done = sum(1 for i in items if i['completed'])
    categories = {}
    for item in items:
        cat = item['category']
        if cat not in categories:
            categories[cat] = {'total': 0, 'done': 0}
        categories[cat]['total'] += 1
        if item['completed']:
            categories[cat]['done'] += 1
    return done, total, items, categories