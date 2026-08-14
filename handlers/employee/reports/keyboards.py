import calendar
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .constants import (
    CB_NOOP,
    CB_REPORT_BACK_MENU,
    CB_REPORT_TO_CALENDAR,
    CB_REPORT_TYPE_PREFIX,
    CB_REPORT_DATE_PREFIX,
    CB_REPORT_PREV_MONTH,
    CB_REPORT_NEXT_MONTH,
    CB_REPORT_CREATE,
    CB_REPORT_EDIT,
    CB_REPORT_VIEW,
    CB_REPORT_TEMPLATE,
    CB_REPORT_SAVE,
    CB_REPORT_REENTER,
    CB_REPORT_CANCEL,
    CB_REPORT_PREV_REPORT,
    MONTHS,
    WEEKDAYS_SHORT,
    REPORT_TYPES,
    REPORT_TYPE_LABELS,
)


def reports_calendar_keyboard(
    report_type: str,
    year: int,
    month: int,
    dates_with_reports: set[str],
    today: str,
) -> InlineKeyboardMarkup:
    rows = []

    # Тип отчёта
    type_row = []

    for rep_type in REPORT_TYPES:
        label = REPORT_TYPE_LABELS.get(rep_type, rep_type)

        if rep_type == report_type:
            label = f"✅ {label}"

        type_row.append(
            InlineKeyboardButton(
                label,
                callback_data=f"{CB_REPORT_TYPE_PREFIX}{rep_type}",
            )
        )

    rows.append(type_row)

    # Навигация по месяцам
    rows.append(
        [
            InlineKeyboardButton("◀️", callback_data=CB_REPORT_PREV_MONTH),
            InlineKeyboardButton(f"{MONTHS[month - 1]} {year}", callback_data=CB_NOOP),
            InlineKeyboardButton("▶️", callback_data=CB_REPORT_NEXT_MONTH),
        ]
    )

    # Дни недели
    rows.append(
        [
            InlineKeyboardButton(day, callback_data=CB_NOOP)
            for day in WEEKDAYS_SHORT
        ]
    )

    first_weekday = datetime(year, month, 1).weekday()
    _, days_in_month = calendar.monthrange(year, month)

    row = []

    for _ in range(first_weekday):
        row.append(InlineKeyboardButton(" ", callback_data=CB_NOOP))

    for day in range(1, days_in_month + 1):
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        date_compact = f"{year:04d}{month:02d}{day:02d}"

        if date_str in dates_with_reports:
            label = f"📌 {day}"
        elif date_str == today:
            label = f"{day} •"
        else:
            label = str(day)

        row.append(
            InlineKeyboardButton(
                label,
                callback_data=f"{CB_REPORT_DATE_PREFIX}{date_compact}",
            )
        )

        if len(row) == 7:
            rows.append(row)
            row = []

    if row:
        while len(row) < 7:
            row.append(InlineKeyboardButton(" ", callback_data=CB_NOOP))
        rows.append(row)

    rows.append(
        [
            InlineKeyboardButton("🏠 Меню", callback_data=CB_REPORT_BACK_MENU)
        ]
    )

    return InlineKeyboardMarkup(rows)


def report_day_keyboard(has_report: bool, prev_exists: bool) -> InlineKeyboardMarkup:
    rows = []

    if has_report:
        rows.append(
            [
                InlineKeyboardButton("👁 Полный текст", callback_data=CB_REPORT_VIEW),
                InlineKeyboardButton("✏️ Изменить", callback_data=CB_REPORT_EDIT),
            ]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton("➕ Создать отчёт", callback_data=CB_REPORT_CREATE)
            ]
        )

    if prev_exists:
        rows.append(
            [
                InlineKeyboardButton("📄 Предыдущий", callback_data=CB_REPORT_PREV_REPORT)
            ]
        )

    rows.append(
        [
            InlineKeyboardButton("📅 Календарь", callback_data=CB_REPORT_TO_CALENDAR),
            InlineKeyboardButton("🏠 Меню", callback_data=CB_REPORT_BACK_MENU),
        ]
    )

    return InlineKeyboardMarkup(rows)


def report_create_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🧾 Шаблон", callback_data=CB_REPORT_TEMPLATE)
            ],
            [
                InlineKeyboardButton("✖️ Отмена", callback_data=CB_REPORT_CANCEL)
            ],
        ]
    )


def report_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Сохранить", callback_data=CB_REPORT_SAVE),
                InlineKeyboardButton("✏️ Заново", callback_data=CB_REPORT_REENTER),
            ],
            [
                InlineKeyboardButton("✖️ Отмена", callback_data=CB_REPORT_CANCEL)
            ],
        ]
    )