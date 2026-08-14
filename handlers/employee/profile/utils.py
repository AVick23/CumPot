import re
from datetime import datetime


def format_date(date_str: str | None) -> str:
    """Форматирует дату из YYYY-MM-DD в DD.MM.YYYY или возвращает '—'."""
    if not date_str:
        return "—"
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%d.%m.%Y")
    except ValueError:
        return date_str


def format_phone(phone: str | None) -> str:
    """Форматирует телефон в удобочитаемый вид (если возможно)."""
    if not phone:
        return "—"
    # Убираем всё, кроме цифр и '+'
    cleaned = re.sub(r"[^\d+]", "", phone)
    if len(cleaned) == 11 and cleaned.startswith("7"):
        return f"+7 ({cleaned[1:4]}) {cleaned[4:7]}-{cleaned[7:9]}-{cleaned[9:11]}"
    if len(cleaned) == 12 and cleaned.startswith("+"):
        return cleaned  # уже с плюсом
    return phone


def validate_phone(phone: str) -> bool:
    """Простая проверка, что номер содержит только цифры и +."""
    return bool(re.fullmatch(r"^\+?\d{10,15}$", phone))


def validate_date(date_str: str) -> bool:
    """Проверяет, что строка соответствует YYYY-MM-DD."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_position(pos: str) -> bool:
    return pos.lower() in ("bar", "kitchen")