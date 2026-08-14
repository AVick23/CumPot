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
    CB_PHOTO_REPORT,
    CB_PHOTO_LOC_PREFIX,
    CB_PHOTO_CAT_PREFIX,
    CB_PHOTO_ALL_LOC,
    CB_PHOTO_ALL_CAT,
    CB_PHOTO_TASK_PREFIX,
    CB_PHOTO_PAGE_PREFIX,
    CB_PHOTO_BACK_DAY,
    CB_PHOTO_BACK_OVERVIEW,
    CB_PHOTO_BACK_LOC,
    CB_TAB_CHECKLIST,
    CB_TAB_SHIFT_REPORTS,
    CB_TAB_TAXI,
    CB_TAXI_PHOTO_REPORT,
    CB_TAXI_PHOTO_USER_PREFIX,
    CB_TAXI_PHOTO_ALL,
    CB_TAXI_PHOTO_BACK,
    REPORT_MODE_SHORT,
    REPORT_MODE_FULL,
    MONTHS,
    WEEKDAYS_SHORT,
    CATEGORY_ORDER,
    CATEGORY_LABELS,
)


def _clip(text: str | None, limit: int = 35) -> str:
    text = " ".join((text or "").split())

    if len(text) <= limit:
        return text

    return text[: limit - 1].rstrip() + "…"


def calendar_keyboard(
    year: int,
    month: int,
    shift_days: set[str],
    selected_date: str | None = None,
    today: str | None = None,
) -> InlineKeyboardMarkup:
    rows = []

    rows.append(
        [
            InlineKeyboardButton("◀️", callback_data=CB_PREV_MONTH),
            InlineKeyboardButton(f"{MONTHS[month - 1]} {year}", callback_data=CB_NOOP),
            InlineKeyboardButton("▶️", callback_data=CB_NEXT_MONTH),
        ]
    )

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


def day_report_tabs_keyboard(current_tab: str) -> InlineKeyboardMarkup:
    """Клавиатура с вкладками для переключения между чек-листами, сменными отчётами и такси."""
    tabs = [
        (CB_TAB_CHECKLIST, "📋 Чек-листы"),
        (CB_TAB_SHIFT_REPORTS, "📄 Сменные отчёты"),
        (CB_TAB_TAXI, "🚕 Такси"),
    ]
    buttons = []
    for tab, label in tabs:
        if tab == current_tab:
            label = f"✅ {label}"
        buttons.append(InlineKeyboardButton(label, callback_data=tab))
    return InlineKeyboardMarkup([buttons])


def taxi_photo_keyboard(has_media: bool, date_str: str) -> InlineKeyboardMarkup:
    """Клавиатура для раздела такси (добавляет кнопку фотоотчёта)."""
    if has_media:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📸 Фотоотчёт по такси", callback_data=CB_TAXI_PHOTO_REPORT)]
        ])
    return None


def day_report_keyboard(
    mode: str,
    show_photos: bool,
    has_bar_media: bool,
    has_kitchen_media: bool,
    current_tab: str,
    taxi_has_media: bool = False,
) -> InlineKeyboardMarkup:
    rows = []

    # Вкладки
    rows.append(day_report_tabs_keyboard(current_tab).inline_keyboard[0])

    # Если текущая вкладка - чек-листы, показываем настройки
    if current_tab == CB_TAB_CHECKLIST:
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

        if show_photos and (has_bar_media or has_kitchen_media):
            rows.append(
                [
                    InlineKeyboardButton(
                        "📸 Фотоотчёт",
                        callback_data=CB_PHOTO_REPORT,
                    )
                ]
            )

    # Если текущая вкладка - такси, показываем кнопку фотоотчёта
    elif current_tab == CB_TAB_TAXI:
        if taxi_has_media:
            rows.append(
                [
                    InlineKeyboardButton(
                        "📸 Фотоотчёт по такси",
                        callback_data=CB_TAXI_PHOTO_REPORT,
                    )
                ]
            )

    # Навигация
    rows.append(
        [
            InlineKeyboardButton("◀️ Календарь", callback_data=CB_TO_CALENDAR),
            InlineKeyboardButton("🏠 Меню", callback_data=CB_HOME),
        ]
    )

    return InlineKeyboardMarkup(rows)


# =========================================================
# Фотоотчёт по такси – клавиатуры
# =========================================================

def taxi_photo_overview_keyboard(users: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for user in users:
        label = f"{user['full_name']} · 🖼{user['media_count']}"
        rows.append([
            InlineKeyboardButton(label, callback_data=f"{CB_TAXI_PHOTO_USER_PREFIX}{user['user_id']}")
        ])
    rows.append([
        InlineKeyboardButton("📤 Отправить все фото", callback_data=CB_TAXI_PHOTO_ALL),
        InlineKeyboardButton("◀️ Назад", callback_data=CB_TAXI_PHOTO_BACK),
    ])
    return InlineKeyboardMarkup(rows)


def taxi_photo_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад к списку", callback_data=CB_TAXI_PHOTO_BACK)]
    ])