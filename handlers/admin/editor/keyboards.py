import calendar
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .constants import (
    CB_HOME,
    CB_TO_EDIT,
    CB_TO_CATEGORIES,
    CB_TO_ITEMS,
    CB_LOC_PREFIX,
    CB_CAT_PREFIX,
    CB_PAGE_PREFIX,
    CB_ITEM_PREFIX,
    CB_EDIT_ITEM_PREFIX,
    CB_DELETE_ITEM_PREFIX,
    CB_CONFIRM_DELETE_PREFIX,
    CB_ADD,
    CB_ADD_PICK,
    CB_CANCEL,
    CB_ITEM_TYPE_PREFIX,
    CB_DATE_PREFIX,
    CB_MONTH_PREV,
    CB_MONTH_NEXT,
    CB_HOUR_PREFIX,
    CB_MINUTE_PREFIX,
    CB_PHOTO_FLAG_PREFIX,
    CB_NOTIF_FLAG_PREFIX,
    CB_TOGGLE_PHOTO,
    CB_TOGGLE_NOTIFICATION,
    CB_CHANGE_TIME,
    CB_CHANGE_DATE,
    CB_ADD_DAY_PREFIX,
    CB_DAY_TOGGLE_PREFIX,
    CB_DAY_PRESET_PREFIX,
    CB_DAYS_SAVE,
    CB_DAYS_CANCEL,
    CB_ADD_BACK_TEXT,
    DAILY_CATEGORIES,
    CATEGORY_LABELS,
    WEEKDAYS_SHORT,
    MONTHS,
)

from .utils import (
    clip,
    get_week_days,
    format_date_short,
    format_date_ru,
)


# =========================================================
# NAVIGATION
# =========================================================

def edit_location_keyboard(counts: dict[str, int]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"Бар · {counts.get('bar', 0)}",
                    callback_data=f"{CB_LOC_PREFIX}:bar",
                )
            ],
            [
                InlineKeyboardButton(
                    f"Кухня · {counts.get('kitchen', 0)}",
                    callback_data=f"{CB_LOC_PREFIX}:kitchen",
                )
            ],
            [
                InlineKeyboardButton(
                    "Добавить пункт",
                    callback_data=CB_ADD_PICK,
                )
            ],
            [
                InlineKeyboardButton(
                    "Главное меню",
                    callback_data=CB_HOME,
                )
            ],
        ]
    )


def edit_category_keyboard(location: str, counts: dict[str, int]) -> InlineKeyboardMarkup:
    rows = []

    for cat_key, cat_label in DAILY_CATEGORIES:
        rows.append(
            [
                InlineKeyboardButton(
                    f"{cat_label} · {counts.get(cat_key, 0)}",
                    callback_data=f"{CB_CAT_PREFIX}:{location}:{cat_key}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                f"{CATEGORY_LABELS['weekly']} · {counts.get('weekly', 0)}",
                callback_data=f"{CB_CAT_PREFIX}:{location}:weekly",
            )
        ]
    )

    rows.append(
        [
            InlineKeyboardButton(
                f"{CATEGORY_LABELS['once']} · {counts.get('once', 0)}",
                callback_data=f"{CB_CAT_PREFIX}:{location}:once",
            )
        ]
    )

    rows.append(
        [
            InlineKeyboardButton("Локации", callback_data=CB_TO_EDIT),
            InlineKeyboardButton("Меню", callback_data=CB_HOME),
        ]
    )

    return InlineKeyboardMarkup(rows)


def items_list_keyboard(
    location: str,
    category: str,
    page_items: list[dict],
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    rows = []

    for item in page_items:
        badges = []

        if item.get("requires_photo"):
            badges.append("📸")

        if item.get("requires_notification"):
            badges.append("🔔")

        if item.get("type") == "weekly":
            days = get_week_days(item)
            if days:
                day_label = " ".join(WEEKDAYS_SHORT[d] for d in days[:2])
                if len(days) > 2:
                    day_label += "…"
                badges.append(day_label)

        elif item.get("type") == "once" and item.get("due_date"):
            badges.append(format_date_short(item.get("due_date")))

        label = clip(item.get("text"), 26)

        if badges:
            label = f"{label} · {' '.join(badges)}"

        rows.append(
            [
                InlineKeyboardButton(
                    label,
                    callback_data=f"{CB_ITEM_PREFIX}:{item.get('id')}",
                )
            ]
        )

    if total_pages > 1:
        nav_row = []

        if page > 1:
            nav_row.append(
                InlineKeyboardButton(
                    "←",
                    callback_data=f"{CB_PAGE_PREFIX}:{location}:{category}:{page - 1}",
                )
            )

        nav_row.append(
            InlineKeyboardButton(
                f"{page}/{total_pages}",
                callback_data="noop",
            )
        )

        if page < total_pages:
            nav_row.append(
                InlineKeyboardButton(
                    "→",
                    callback_data=f"{CB_PAGE_PREFIX}:{location}:{category}:{page + 1}",
                )
            )

        rows.append(nav_row)

    rows.append(
        [
            InlineKeyboardButton("Добавить пункт", callback_data=CB_ADD)
        ]
    )

    rows.append(
        [
            InlineKeyboardButton("Разделы", callback_data=CB_TO_CATEGORIES),
            InlineKeyboardButton("Меню", callback_data=CB_HOME),
        ]
    )

    return InlineKeyboardMarkup(rows)


# =========================================================
# ITEM DETAIL
# =========================================================

def item_detail_keyboard(item: dict) -> InlineKeyboardMarkup:
    item_id = item.get("id")

    photo_on = bool(item.get("requires_photo"))
    notif_on = bool(item.get("requires_notification"))
    notif_time = item.get("notification_time") or "—"

    rows = [
        [
            InlineKeyboardButton(
                "Изменить текст",
                callback_data=f"{CB_EDIT_ITEM_PREFIX}:{item_id}",
            )
        ]
    ]

    if item.get("type") == "weekly":
        days = get_week_days(item)
        if days:
            days_label = ", ".join(WEEKDAYS_SHORT[d] for d in days)
        else:
            days_label = "не выбраны"

        rows.append(
            [
                InlineKeyboardButton(
                    f"Дни: {days_label}",
                    callback_data=f"{CB_ADD_DAY_PREFIX}:{item_id}",
                )
            ]
        )

    elif item.get("type") == "once":
        date_label = format_date_ru(item.get("due_date")) or "не задана"
        rows.append(
            [
                InlineKeyboardButton(
                    f"Дата: {date_label}",
                    callback_data=f"{CB_CHANGE_DATE}:{item_id}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                f"Фото: {'Вкл' if photo_on else 'Выкл'}",
                callback_data=f"{CB_TOGGLE_PHOTO}:{item_id}",
            )
        ]
    )

    rows.append(
        [
            InlineKeyboardButton(
                f"Уведомление: {'Вкл' if notif_on else 'Выкл'}",
                callback_data=f"{CB_TOGGLE_NOTIFICATION}:{item_id}",
            )
        ]
    )

    if notif_on:
        rows.append(
            [
                InlineKeyboardButton(
                    f"Время: {notif_time}",
                    callback_data=f"{CB_CHANGE_TIME}:{item_id}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                "Удалить",
                callback_data=f"{CB_DELETE_ITEM_PREFIX}:{item_id}",
            ),
            InlineKeyboardButton(
                "Назад",
                callback_data=CB_TO_ITEMS,
            ),
        ]
    )

    return InlineKeyboardMarkup(rows)


def confirm_delete_keyboard(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Да, удалить",
                    callback_data=f"{CB_CONFIRM_DELETE_PREFIX}:{item_id}",
                ),
                InlineKeyboardButton(
                    "Отмена",
                    callback_data=f"{CB_ITEM_PREFIX}:{item_id}",
                ),
            ]
        ]
    )


# =========================================================
# ADD FLOW KEYBOARDS
# =========================================================

def text_prompt_keyboard(back_callback: str, cancel_callback: str | None = None) -> InlineKeyboardMarkup:
    row = [
        InlineKeyboardButton("Назад", callback_data=back_callback)
    ]

    if cancel_callback and cancel_callback != back_callback:
        row.append(
            InlineKeyboardButton("Отмена", callback_data=cancel_callback)
        )

    return InlineKeyboardMarkup([row])


def item_type_keyboard() -> InlineKeyboardMarkup:
    """
    Оставлена на будущее, если вы захотите выбирать тип отдельно.
    В текущем UX тип определяется разделом.
    """
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Ежедневно",
                    callback_data=f"{CB_ITEM_TYPE_PREFIX}:daily",
                )
            ],
            [
                InlineKeyboardButton(
                    "По дням недели",
                    callback_data=f"{CB_ITEM_TYPE_PREFIX}:weekly",
                )
            ],
            [
                InlineKeyboardButton(
                    "Один раз",
                    callback_data=f"{CB_ITEM_TYPE_PREFIX}:once",
                )
            ],
            [
                InlineKeyboardButton(
                    "Отмена",
                    callback_data=CB_CANCEL,
                )
            ],
        ]
    )


def days_selection_keyboard(selected_days: set[int]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("Все", callback_data=f"{CB_DAY_PRESET_PREFIX}:all"),
            InlineKeyboardButton("Будни", callback_data=f"{CB_DAY_PRESET_PREFIX}:weekdays"),
            InlineKeyboardButton("Выходные", callback_data=f"{CB_DAY_PRESET_PREFIX}:weekend"),
        ]
    ]

    day_rows = []

    for i in range(0, 7, 2):
        row = []

        for j in (i, i + 1):
            if j >= 7:
                continue

            label = f"✅ {WEEKDAYS_SHORT[j]}" if j in selected_days else WEEKDAYS_SHORT[j]
            row.append(
                InlineKeyboardButton(
                    label,
                    callback_data=f"{CB_DAY_TOGGLE_PREFIX}:{j}",
                )
            )

        if row:
            day_rows.append(row)

    rows.extend(day_rows)

    rows.append(
        [
            InlineKeyboardButton("Готово", callback_data=CB_DAYS_SAVE),
            InlineKeyboardButton("Отмена", callback_data=CB_DAYS_CANCEL),
        ]
    )

    return InlineKeyboardMarkup(rows)


def calendar_keyboard(year: int, month: int, selected_date: str | None = None) -> InlineKeyboardMarkup:
    rows = []

    rows.append(
        [
            InlineKeyboardButton("←", callback_data=CB_MONTH_PREV),
            InlineKeyboardButton(f"{MONTHS[month - 1]} {year}", callback_data="noop"),
            InlineKeyboardButton("→", callback_data=CB_MONTH_NEXT),
        ]
    )

    rows.append(
        [
            InlineKeyboardButton(day, callback_data="noop")
            for day in WEEKDAYS_SHORT
        ]
    )

    first_weekday = datetime(year, month, 1).weekday()
    _, days_in_month = calendar.monthrange(year, month)

    row = []

    for _ in range(first_weekday):
        row.append(InlineKeyboardButton(" ", callback_data="noop"))

    for day in range(1, days_in_month + 1):
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        label = f"✅ {day}" if selected_date == date_str else str(day)

        row.append(
            InlineKeyboardButton(
                label,
                callback_data=f"{CB_DATE_PREFIX}:{date_str}",
            )
        )

        if len(row) == 7:
            rows.append(row)
            row = []

    if row:
        while len(row) < 7:
            row.append(InlineKeyboardButton(" ", callback_data="noop"))
        rows.append(row)

    rows.append(
        [
            InlineKeyboardButton("Назад", callback_data=CB_CANCEL),
            InlineKeyboardButton("Домой", callback_data=CB_HOME),
        ]
    )

    return InlineKeyboardMarkup(rows)


def hour_keyboard(selected_hour: int | None = None) -> InlineKeyboardMarkup:
    rows = []
    row = []

    for h in range(24):
        label = f"✅ {h:02d}" if selected_hour == h else f"{h:02d}"
        row.append(
            InlineKeyboardButton(
                label,
                callback_data=f"{CB_HOUR_PREFIX}:{h}",
            )
        )

        if len(row) == 6:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append(
        [
            InlineKeyboardButton("Назад", callback_data=CB_CANCEL),
            InlineKeyboardButton("Домой", callback_data=CB_HOME),
        ]
    )

    return InlineKeyboardMarkup(rows)


def minute_keyboard(selected_minute: int | None = None) -> InlineKeyboardMarkup:
    rows = []
    row = []

    for m in range(0, 60, 5):
        label = f"✅ {m:02d}" if selected_minute == m else f"{m:02d}"
        row.append(
            InlineKeyboardButton(
                label,
                callback_data=f"{CB_MINUTE_PREFIX}:{m}",
            )
        )

        if len(row) == 4:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append(
        [
            InlineKeyboardButton("Назад", callback_data=CB_CANCEL),
            InlineKeyboardButton("Домой", callback_data=CB_HOME),
        ]
    )

    return InlineKeyboardMarkup(rows)


def flag_photo_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Да", callback_data=f"{CB_PHOTO_FLAG_PREFIX}:yes")
            ],
            [
                InlineKeyboardButton("Нет", callback_data=f"{CB_PHOTO_FLAG_PREFIX}:no")
            ],
            [
                InlineKeyboardButton("Назад", callback_data=CB_ADD_BACK_TEXT),
                InlineKeyboardButton("Отмена", callback_data=CB_CANCEL),
            ],
        ]
    )


def flag_notification_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Да", callback_data=f"{CB_NOTIF_FLAG_PREFIX}:yes")
            ],
            [
                InlineKeyboardButton("Нет", callback_data=f"{CB_NOTIF_FLAG_PREFIX}:no")
            ],
            [
                InlineKeyboardButton("Назад", callback_data=CB_ADD_BACK_TEXT),
                InlineKeyboardButton("Отмена", callback_data=CB_CANCEL),
            ],
        ]
    )