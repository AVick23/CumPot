from datetime import datetime

def format_date(date_str: str | None) -> str:
    if not date_str:
        return "—"
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%d.%m.%Y")
    except ValueError:
        return date_str

def format_phone(phone: str | None) -> str:
    if not phone:
        return "—"
    # Можно добавить форматирование, если нужно
    return phone