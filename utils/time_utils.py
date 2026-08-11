from datetime import datetime, timezone, timedelta

# Фиксированный часовой пояс МСК (+3)
MSK_TZ = timezone(timedelta(hours=3))


def now_msk() -> datetime:
    """Текущее время строго по МСК"""
    return datetime.now(MSK_TZ)


def today_msk_str() -> str:
    """Дата сегодня по МСК в формате YYYY-MM-DD"""
    return now_msk().strftime("%Y-%m-%d")


def time_msk_str() -> str:
    """Время сейчас по МСК в формате HH:MM:SS"""
    return now_msk().strftime("%H:%M:%S")


def parse_date(date_str: str) -> datetime:
    """Парсит строку даты YYYY-MM-DD как дату по МСК"""
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=MSK_TZ)