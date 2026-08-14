import calendar
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .constants import (
    CB_NOOP,
    CB_REPORT_BACK_MENU,
    CB_REPORT_HOME,
    CB_REPORT_HISTORY,
    CB_REPORT_OPEN_PREFIX,
    CB_REPORT_TYPE_PREFIX,
    CB_REPORT_DATE_PREFIX,
    CB_REPORT_PREV_MONTH,
    CB_REPORT_NEXT_MONTH,
    CB_REPORT_SAVE,
    CB_REPORT_TEXT_MODE,
    CB_REPORT_LOAD_PREV,
    CB_REPORT_CLEAR,
    CB_REPORT_SECTION_PREFIX,
    CB_REPORT_BACK_EDITOR,
    CB_REPORT_CANCEL,
    MONTHS,
    WEEKDAYS_SHORT,
    REPORT_TYPE_LABELS,
)


def _clip(text: str | None, limit: int = 35) -> str:
    text = " ".join((text or "").split())

    if len(text) <= limit:
        return text

    return text[: limit - 1].rstrip() + "…"


def today_dashboard_keyboard(
    opening_exists: bool,
    closing_exists: bool,
) -> InlineKeyboardMarkup:
    opening_label = f"{'✅' if opening_exists else '⚪️'} 📋 Открытие"
    closing_label = f"{'✅' if closing_exists else '⚪️'} 🌙 Закрытие"

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    opening_label,
                    callback_data=f"{CB_REPORT_OPEN_PREFIX}opening",
                )
            ],
            [
                InlineKeyboardButton(
                    closing_label,
                    callback_data=f"{CB_REPORT_OPEN_PREFIX}closing",
                )
            ],
            [
                InlineKeyboardButton("🗓 История", callback_data=CB_REPORT_HISTORY),
                InlineKeyboardButton("🏠 Меню", callback_data=CB_REPORT_BACK_MENU),
            ],
        ]
    )


def history_calendar_keyboard(
    report_type: str,
    year: int,
    month: int,
    dates_with_reports: set[str],
    today: str,
) -> InlineKeyboardMarkup:
    rows = []

    # Переключение типа отчёта
    type_row = []

    for rep_type in ["opening", "closing"]:
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

    # Месяц
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
            InlineKeyboardButton("◀️ Сегодня", callback_data=CB_REPORT_HOME),
            InlineKeyboardButton("🏠 Меню", callback_data=CB_REPORT_BACK_MENU),
        ]
    )

    return InlineKeyboardMarkup(rows)


def report_editor_keyboard(draft: dict) -> InlineKeyboardMarkup:
    rows = []

    # Основные действия
    rows.append(
        [
            InlineKeyboardButton("✅ Сохранить", callback_data=CB_REPORT_SAVE)
        ]
    )

    rows.append(
        [
            InlineKeyboardButton("🧾 Текстом", callback_data=CB_REPORT_TEXT_MODE),
            InlineKeyboardButton("📋 Последний", callback_data=CB_REPORT_LOAD_PREV),
        ]
    )

    rows.append(
        [
            InlineKeyboardButton("🗑 Очистить", callback_data=CB_REPORT_CLEAR),
            InlineKeyboardButton("✖️ Отмена", callback_data=CB_REPORT_CANCEL),
        ]
    )

    # Разделы
    order = draft.get("order", [])
    values = draft.get("values", {})

    for index, section in enumerate(order):
        value = (values.get(section) or "").strip()
        icon = "✅" if value else "⚪️"

        rows.append(
            [
                InlineKeyboardButton(
                    f"{icon} {section}",
                    callback_data=f"{CB_REPORT_SECTION_PREFIX}{index}",
                )
            ]
        )

    return InlineKeyboardMarkup(rows)


def section_prompt_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("◀️ Назад", callback_data=CB_REPORT_BACK_EDITOR),
                InlineKeyboardButton("✖️ Отмена", callback_data=CB_REPORT_CANCEL),
            ]
        ]
    )


def text_prompt_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("◀️ Назад", callback_data=CB_REPORT_BACK_EDITOR),
                InlineKeyboardButton("✖️ Отмена", callback_data=CB_REPORT_CANCEL),
            ]
        ]
    )