import calendar
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .constants import (
    CB_HOME,
    CB_TO_CALENDAR,
    CB_PREV_MONTH,
    CB_NEXT_MONTH,
    CB_DAY_PREFIX,
    CB_NOOP,
    CB_REPORT_SHORT,
    CB_REPORT_FULL,
    CB_REPORT_PHOTOS_ON,
    CB_REPORT_PHOTOS_OFF,
    CB_SHOW_MEDIA_PREFIX,
    REPORT_MODE_SHORT,
    REPORT_MODE_FULL,
    MONTHS,
    WEEKDAYS_SHORT,
)


def calendar_keyboard(
    year: int,
    month: int,
    shift_days: set[str],
    selected_date: str | None = None,
    today: str | None = None,
) -> InlineKeyboardMarkup:
    rows = []

    # Шапка месяца
    rows.append(
        [
            InlineKeyboardButton("◀️", callback_data=CB_PREV_MONTH),
            InlineKeyboardButton(f"{MONTHS[month - 1]} {year}", callback_data=CB_NOOP),
            InlineKeyboardButton("▶️", callback_data=CB_NEXT_MONTH),
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

    # Пустые клетки до первого дня месяца
    for _ in range(first_weekday):
        row.append(InlineKeyboardButton(" ", callback_data=CB_NOOP))

    for day in range(1, days_in_month + 1):
        date_db = f"{year:04d}-{month:02d}-{day:02d}"
        date_compact = f"{year:04d}{month:02d}{day:02d}"

        if selected_date == date_db:
            label = f"🔹 {day}"
        elif date_db in shift_days:
            label = f"✅ {day}"
        elif today == date_db:
            label = f"{day}·"
        else:
            label = str(day)

        row.append(
            InlineKeyboardButton(
                label,
                callback_data=f"{CB_DAY_PREFIX}:{date_compact}",
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
            InlineKeyboardButton("🏠 Меню", callback_data=CB_HOME)
        ]
    )

    return InlineKeyboardMarkup(rows)


def day_report_keyboard(
    mode: str,
    show_photos: bool,
    has_bar_media: bool,
    has_kitchen_media: bool,
) -> InlineKeyboardMarkup:
    rows = []

    # Режим отчёта
    rows.append(
        [
            InlineKeyboardButton(
                f"{'✅ ' if mode == REPORT_MODE_SHORT else ''}Кратко",
                callback_data=CB_REPORT_SHORT,
            ),
            InlineKeyboardButton(
                f"{'✅ ' if mode == REPORT_MODE_FULL else ''}Полный",
                callback_data=CB_REPORT_FULL,
            ),
        ]
    )

    # Фото в отчёте
    rows.append(
        [
            InlineKeyboardButton(
                f"{'✅ ' if show_photos else ''}С фото",
                callback_data=CB_REPORT_PHOTOS_ON,
            ),
            InlineKeyboardButton(
                f"{'✅ ' if not show_photos else ''}Без фото",
                callback_data=CB_REPORT_PHOTOS_OFF,
            ),
        ]
    )

    # Кнопки отправки медиа, если фото включены и есть вложения
    if show_photos:
        media_row = []

        if has_bar_media:
            media_row.append(
                InlineKeyboardButton(
                    "📸 Бар",
                    callback_data=f"{CB_SHOW_MEDIA_PREFIX}:bar",
                )
            )

        if has_kitchen_media:
            media_row.append(
                InlineKeyboardButton(
                    "📸 Кухня",
                    callback_data=f"{CB_SHOW_MEDIA_PREFIX}:kitchen",
                )
            )

        if media_row:
            rows.append(media_row)

    rows.append(
        [
            InlineKeyboardButton("◀️ Календарь", callback_data=CB_TO_CALENDAR),
            InlineKeyboardButton("🏠 Меню", callback_data=CB_HOME),
        ]
    )

    return InlineKeyboardMarkup(rows)