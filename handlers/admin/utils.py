from db.shifts import get_shifts_for_date
from datetime import datetime

def get_today_shifts():
    date = datetime.now().strftime("%Y-%m-%d")
    return get_shifts_for_date(date)