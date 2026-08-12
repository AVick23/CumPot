import calendar
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .constants import (
    CB_HOME, CB_PREV_MONTH, CB_NEXT_MONTH, CB_DAY_PREFIX,
    WEEKDAYS_SHORT, MONTHS, CB_TO_CALENDAR
)


def calendar_keyboard(year: int, month: int, shift_days: set[str]) -> InlineKeyboardMarkup:
    rows = []
    rows.append([
        InlineKeyboardButton("◀️", callback_data=CB_PREV_MONTH),
        InlineKeyboardButton(f"{MONTHS[month - 1]} {year}", callback_data="noop"),
        InlineKeyboardButton("▶️", callback_data=CB_NEXT_MONTH),
    ])
    rows.append([InlineKeyboardButton(day, callback_data="noop") for day in WEEKDAYS_SHORT])

    first_weekday = datetime(year, month, 1).weekday()
    _, days_in_month = calendar.monthrange(year, month)

    row = []
    for _ in range(first_weekday):
        row.append(InlineKeyboardButton(" ", callback_data="noop"))

    for day in range(1, days_in_month + 1):
        date_db = f"{year:04d}-{month:02d}-{day:02d}"
        date_compact = f"{year:04d}{month:02d}{day:02d}"
        label = f"✅ {day}" if date_db in shift_days else str(day)
        row.append(InlineKeyboardButton(label, callback_data=f"{CB_DAY_PREFIX}:{date_compact}"))
        if len(row) == 7:
            rows.append(row)
            row = []

    if row:
        while len(row) < 7:
            row.append(InlineKeyboardButton(" ", callback_data="noop"))
        rows.append(row)

    rows.append([
        InlineKeyboardButton("🏠 Меню", callback_data=CB_HOME),
    ])
    return InlineKeyboardMarkup(rows)


def day_report_keyboard(has_bar_media: bool = False, has_kitchen_media: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if has_bar_media:
        rows.append([InlineKeyboardButton("🍸 Показать вложения (Бар)", callback_data="show_media:bar")])
    if has_kitchen_media:
        rows.append([InlineKeyboardButton("🍳 Показать вложения (Кухня)", callback_data="show_media:kitchen")])
    rows.append([InlineKeyboardButton("◀️ Календарь", callback_data=CB_TO_CALENDAR)])
    rows.append([InlineKeyboardButton("🏠 Меню", callback_data=CB_HOME)])
    return InlineKeyboardMarkup(rows)