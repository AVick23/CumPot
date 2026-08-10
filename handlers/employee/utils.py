from db.shifts import start_shift, get_active_shift, end_shift
from db.checklist import get_items_for_location_and_day, save_progress, get_progress_for_user_date
from datetime import datetime

def mark_shift(user_id, location):
    start_shift(user_id, location)

def get_current_shift(user_id):
    return get_active_shift(user_id)

def end_current_shift(user_id):
    end_shift(user_id)

def get_checklist_items(user_id, context):
    shift = get_active_shift(user_id)
    if not shift:
        return None
    location = shift['location']
    day_of_week = datetime.now().weekday()
    date = datetime.now().strftime("%Y-%m-%d")

    items = get_items_for_location_and_day(location, day_of_week)
    if not items:
        return []

    progress = get_progress_for_user_date(user_id, date)
    progress_dict = {p['item_id']: p['completed'] for p in progress}

    for item in items:
        item['completed'] = progress_dict.get(item['id'], 0) == 1

    return items

def get_items_by_category(user_id, context, category):
    all_items = get_checklist_items(user_id, context)
    if not all_items:
        return None
    return [item for item in all_items if item['category'] == category]

def get_item_by_id(user_id, item_id, context):
    all_items = get_checklist_items(user_id, context)
    if not all_items:
        return None
    for item in all_items:
        if item['id'] == item_id:
            return item
    return None

def mark_item_done(user_id, item_id, context):
    date = datetime.now().strftime("%Y-%m-%d")
    progress_list = get_progress_for_user_date(user_id, date)
    progress_dict = {p['item_id']: p['completed'] for p in progress_list}
    current = progress_dict.get(item_id, 0)
    if current == 1:
        return False
    save_progress(user_id, item_id, True)
    return True

def mark_item_undone(user_id, item_id, context):
    date = datetime.now().strftime("%Y-%m-%d")
    progress_list = get_progress_for_user_date(user_id, date)
    progress_dict = {p['item_id']: p['completed'] for p in progress_list}
    current = progress_dict.get(item_id, 0)
    if current == 0:
        return False
    save_progress(user_id, item_id, False)
    return True

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