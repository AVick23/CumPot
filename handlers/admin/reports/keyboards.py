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
    CATEGORY_LABELS,
    LOCATIONS,
)


def _clip(text, limit=35):
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def calendar_keyboard(
    year,
    month,
    shift_days,
    selected_date=None,
    today=None,
):
    rows = []

    rows.append(
        [
            InlineKeyboardButton("←", callback_data=CB_PREV_MONTH),
            InlineKeyboardButton(f"{MONTHS[month - 1]} {year}", callback_data=CB_NOOP),
            InlineKeyboardButton("→", callback_data=CB_NEXT_MONTH),
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
            label = f"● {day}"
        elif date_db in shift_days:
            label = f"✓ {day}"
        elif today == date_db:
            label = f"{day} •"
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
            InlineKeyboardButton("Меню", callback_data=CB_HOME),
        ]
    )

    return InlineKeyboardMarkup(rows)


def day_report_tabs_keyboard(current_tab):
    tabs = [
        (CB_TAB_CHECKLIST, "Чек-листы"),
        (CB_TAB_SHIFT_REPORTS, "Смены"),
        (CB_TAB_TAXI, "Такси"),
    ]

    buttons = []

    for tab, label in tabs:
        if tab == current_tab:
            label = f"● {label}"
        buttons.append(InlineKeyboardButton(label, callback_data=tab))

    return InlineKeyboardMarkup([buttons])


def taxi_photo_keyboard(has_media, date_str=None):
    if has_media:
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Фото",
                        callback_data=CB_TAXI_PHOTO_REPORT,
                    )
                ]
            ]
        )
    return None


def day_report_keyboard(
    mode,
    show_photos,
    has_bar_media,
    has_kitchen_media,
    current_tab,
    taxi_has_media=False,
):
    rows = []

    rows.extend(day_report_tabs_keyboard(current_tab).inline_keyboard)

    if current_tab == CB_TAB_CHECKLIST:
        rows.append(
            [
                InlineKeyboardButton(
                    f"{'● ' if mode == REPORT_MODE_SHORT else ''}Кратко",
                    callback_data=CB_REPORT_SHORT,
                ),
                InlineKeyboardButton(
                    f"{'● ' if mode == REPORT_MODE_FULL else ''}Полный",
                    callback_data=CB_REPORT_FULL,
                ),
            ]
        )

        rows.append(
            [
                InlineKeyboardButton(
                    f"{'● ' if show_photos else ''}С фото",
                    callback_data=CB_REPORT_PHOTOS_ON,
                ),
                InlineKeyboardButton(
                    f"{'● ' if not show_photos else ''}Без фото",
                    callback_data=CB_REPORT_PHOTOS_OFF,
                ),
            ]
        )

        if show_photos and (has_bar_media or has_kitchen_media):
            rows.append(
                [
                    InlineKeyboardButton(
                        "Фотоотчёт",
                        callback_data=CB_PHOTO_REPORT,
                    )
                ]
            )

    elif current_tab == CB_TAB_TAXI:
        if taxi_has_media:
            rows.append(
                [
                    InlineKeyboardButton(
                        "Фотоотчёт",
                        callback_data=CB_TAXI_PHOTO_REPORT,
                    )
                ]
            )

    rows.append(
        [
            InlineKeyboardButton("← Календарь", callback_data=CB_TO_CALENDAR),
            InlineKeyboardButton("Меню", callback_data=CB_HOME),
        ]
    )

    return InlineKeyboardMarkup(rows)


# =========================================================
# Фотоотчёт по чек-листам
# =========================================================
def photo_overview_keyboard(bar_media_count, kitchen_media_count):
    rows = []

    if bar_media_count > 0:
        rows.append(
            [
                InlineKeyboardButton(
                    f"{LOCATIONS.get('bar', 'Бар')} · {bar_media_count}",
                    callback_data=f"{CB_PHOTO_LOC_PREFIX}:bar",
                )
            ]
        )

    if kitchen_media_count > 0:
        rows.append(
            [
                InlineKeyboardButton(
                    f"{LOCATIONS.get('kitchen', 'Кухня')} · {kitchen_media_count}",
                    callback_data=f"{CB_PHOTO_LOC_PREFIX}:kitchen",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton("← Отчёт", callback_data=CB_PHOTO_BACK_DAY),
            InlineKeyboardButton("Меню", callback_data=CB_HOME),
        ]
    )

    return InlineKeyboardMarkup(rows)


def photo_location_keyboard(location_menu):
    rows = []

    total_media = location_menu.get("total_media", 0)

    if total_media > 0:
        rows.append(
            [
                InlineKeyboardButton(
                    f"Отправить всё · {total_media}",
                    callback_data=CB_PHOTO_ALL_LOC,
                )
            ]
        )

    categories = location_menu.get("categories", {})

    for category, cat_data in categories.items():
        media_count = cat_data.get("media_count", 0)
        if media_count <= 0:
            continue

        label = f"{CATEGORY_LABELS.get(category, category)} · {media_count}"

        rows.append(
            [
                InlineKeyboardButton(
                    label,
                    callback_data=f"{CB_PHOTO_CAT_PREFIX}:{category}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton("← Локации", callback_data=CB_PHOTO_BACK_OVERVIEW),
            InlineKeyboardButton("Меню", callback_data=CB_HOME),
        ]
    )

    return InlineKeyboardMarkup(rows)


def photo_category_keyboard(
    location,
    category,
    page_items,
    page,
    total_pages,
):
    rows = []

    rows.append(
        [
            InlineKeyboardButton(
                "Отправить всю категорию",
                callback_data=CB_PHOTO_ALL_CAT,
            )
        ]
    )

    for item in page_items:
        media_count = item.get("media_count", 0)
        text = _clip(item.get("text"), 30)
        label = f"{text} · {media_count}"

        rows.append(
            [
                InlineKeyboardButton(
                    label,
                    callback_data=f"{CB_PHOTO_TASK_PREFIX}:{item.get('id')}",
                )
            ]
        )

    if total_pages > 1:
        nav_row = []

        if page > 1:
            nav_row.append(
                InlineKeyboardButton(
                    "←",
                    callback_data=f"{CB_PHOTO_PAGE_PREFIX}:{page - 1}",
                )
            )

        nav_row.append(
            InlineKeyboardButton(
                f"{page}/{total_pages}",
                callback_data=CB_NOOP,
            )
        )

        if page < total_pages:
            nav_row.append(
                InlineKeyboardButton(
                    "→",
                    callback_data=f"{CB_PHOTO_PAGE_PREFIX}:{page + 1}",
                )
            )

        rows.append(nav_row)

    rows.append(
        [
            InlineKeyboardButton("← Категории", callback_data=CB_PHOTO_BACK_LOC),
            InlineKeyboardButton("Меню", callback_data=CB_HOME),
        ]
    )

    return InlineKeyboardMarkup(rows)


# =========================================================
# Фотоотчёт по такси
# =========================================================
def taxi_photo_overview_keyboard(users):
    rows = []

    for user in users:
        name = user.get("full_name") or "Сотрудник"
        media_count = user.get("media_count", 0)

        rows.append(
            [
                InlineKeyboardButton(
                    f"{name} · {media_count}",
                    callback_data=f"{CB_TAXI_PHOTO_USER_PREFIX}:{user.get('user_id')}",
                )
            ]
        )

    if users:
        rows.append(
            [
                InlineKeyboardButton(
                    "Отправить всё",
                    callback_data=CB_TAXI_PHOTO_ALL,
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton("← Отчёт", callback_data=CB_TAXI_PHOTO_BACK),
            InlineKeyboardButton("Меню", callback_data=CB_HOME),
        ]
    )

    return InlineKeyboardMarkup(rows)


def taxi_photo_back_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "← Назад к списку",
                    callback_data=CB_TAXI_PHOTO_BACK,
                )
            ]
        ]
    )