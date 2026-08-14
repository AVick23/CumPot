from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import calendar
from datetime import datetime
from .constants import (
    CB_REPORT_BACK_MENU,
    CB_REPORT_OPENING,
    CB_REPORT_CLOSING,
    CB_REPORT_DATE_PREFIX,
    CB_REPORT_PREV_MONTH,
    CB_REPORT_NEXT_MONTH,
    CB_REPORT_CREATE,
    CB_REPORT_VIEW,
    CB_REPORT_CANCEL,
    CB_REPORT_SAVE,
    MONTHS,
    WEEKDAYS_SHORT,
)


def report_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Открытие", callback_data=CB_REPORT_OPENING)],
        [InlineKeyboardButton("🌙 Закрытие", callback_data=CB_REPORT_CLOSING)],
        [InlineKeyboardButton("◀️ В меню", callback_data=CB_REPORT_BACK_MENU)],
    ])


def calendar_keyboard(year: int, month: int, dates_with_reports: set[str]) -> InlineKeyboardMarkup:
    rows = []
    rows.append([
        InlineKeyboardButton("◀️", callback_data=CB_REPORT_PREV_MONTH),
        InlineKeyboardButton(f"{MONTHS[month-1]} {year}", callback_data="noop"),
        InlineKeyboardButton("▶️", callback_data=CB_REPORT_NEXT_MONTH),
    ])
    rows.append([InlineKeyboardButton(day, callback_data="noop") for day in WEEKDAYS_SHORT])

    first_weekday = datetime(year, month, 1).weekday()
    _, days_in_month = calendar.monthrange(year, month)

    row = []
    for _ in range(first_weekday):
        row.append(InlineKeyboardButton(" ", callback_data="noop"))

    today = datetime.now().strftime("%Y-%m-%d")
    for day in range(1, days_in_month + 1):
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        date_compact = f"{year:04d}{month:02d}{day:02d}"
        if date_str in dates_with_reports:
            label = f"📌{day}"
        elif date_str == today:
            label = f"·{day}"
        else:
            label = str(day)
        row.append(InlineKeyboardButton(label, callback_data=f"{CB_REPORT_DATE_PREFIX}{date_compact}"))
        if len(row) == 7:
            rows.append(row)
            row = []
    if row:
        while len(row) < 7:
            row.append(InlineKeyboardButton(" ", callback_data="noop"))
        rows.append(row)

    rows.append([InlineKeyboardButton("◀️ Назад", callback_data=CB_REPORT_BACK_MENU)])
    return InlineKeyboardMarkup(rows)


def report_action_keyboard(date_str: str, report_type: str, has_report: bool) -> InlineKeyboardMarkup:
    rows = []
    if has_report:
        rows.append([InlineKeyboardButton("👁️ Просмотреть", callback_data=CB_REPORT_VIEW)])
        rows.append([InlineKeyboardButton("✏️ Создать новый (перезаписать)", callback_data=CB_REPORT_CREATE)])
    else:
        rows.append([InlineKeyboardButton("➕ Создать отчёт", callback_data=CB_REPORT_CREATE)])
    rows.append([InlineKeyboardButton("◀️ Выбрать дату", callback_data=CB_REPORT_BACK_MENU)])
    return InlineKeyboardMarkup(rows)


def create_report_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Сохранить и опубликовать", callback_data=CB_REPORT_SAVE)],
        [InlineKeyboardButton("✖️ Отмена", callback_data=CB_REPORT_CANCEL)],
    ])