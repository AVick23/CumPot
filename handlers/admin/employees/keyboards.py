from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .constants import (
    CB_EMP_HOME,
    CB_EMP_ANALYTICS,
    CB_EMP_XLSX_ALL,
    CB_EMP_DETAIL_PREFIX,
    CB_EMP_PROFILE_PREFIX,
    CB_EMP_RATE_PREFIX,
    CB_EMP_STATUS_PREFIX,
    CB_EMP_COMMENT_PREFIX,
    CB_EMP_SHIFTS_PREFIX,
    CB_EMP_TAXI_PREFIX,
    CB_EMP_REPORTS_PREFIX,
    CB_EMP_CHECKLISTS_PREFIX,
    CB_EMP_XLSX_ONE_PREFIX,
    CB_EMP_TAXI_PHOTOS_PREFIX,
    CB_EMP_SET_STATUS_PREFIX,
    CB_EMP_BACK,
    CB_EMP_CANCEL,
    CB_EMP_DELETE,
    CB_EMP_DELETE_SOFT,
    CB_EMP_DELETE_HARD,
    CB_EMP_HIDDEN,
    CB_EMP_RESTORE_PREFIX,
    STATUSES,
)


def employees_list_keyboard(users: list[dict], has_hidden: bool = False) -> InlineKeyboardMarkup:
    rows = []

    for user in users:
        name = (
            user.get("full_name")
            or user.get("first_name")
            or f"ID {user['tg_id']}"
        )

        status_icon = "👤" if user.get("status") == "Сотрудник" else "🎓"
        rows.append(
            [
                InlineKeyboardButton(
                    f"{status_icon} {name}",
                    callback_data=f"{CB_EMP_DETAIL_PREFIX}{user['tg_id']}",
                )
            ]
        )

    # Кнопка "Скрытые" – появляется, если есть хотя бы один скрытый сотрудник
    if has_hidden:
        rows.append(
            [
                InlineKeyboardButton(
                    "🙈 Скрытые сотрудники",
                    callback_data=CB_EMP_HIDDEN,
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton("📊 Аналитика команды", callback_data=CB_EMP_ANALYTICS)
        ]
    )
    rows.append(
        [
            InlineKeyboardButton("🏠 Меню", callback_data=CB_EMP_HOME)
        ]
    )

    return InlineKeyboardMarkup(rows)


def hidden_list_keyboard(users: list[dict]) -> InlineKeyboardMarkup:
    """Клавиатура для списка скрытых сотрудников (с возможностью восстановить или удалить)."""
    rows = []
    for user in users:
        name = (
            user.get("full_name")
            or user.get("first_name")
            or f"ID {user['tg_id']}"
        )
        rows.append(
            [
                InlineKeyboardButton(
                    f"👤 {name}",
                    callback_data=f"{CB_EMP_DETAIL_PREFIX}{user['tg_id']}",
                )
            ]
        )
        # Кнопки действий для каждого скрытого
        rows.append(
            [
                InlineKeyboardButton(
                    "↩️ Восстановить",
                    callback_data=f"{CB_EMP_RESTORE_PREFIX}{user['tg_id']}",
                ),
                InlineKeyboardButton(
                    "🗑 Удалить полностью",
                    callback_data=f"{CB_EMP_DELETE_HARD}:{user['tg_id']}",
                ),
            ]
        )

    rows.append(
        [
            InlineKeyboardButton("◀️ Назад к списку", callback_data=CB_EMP_BACK)
        ]
    )
    return InlineKeyboardMarkup(rows)


def employee_detail_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("👤 Профиль", callback_data=f"{CB_EMP_PROFILE_PREFIX}{user_id}"),
                InlineKeyboardButton("💰 Ставка", callback_data=f"{CB_EMP_RATE_PREFIX}{user_id}"),
            ],
            [
                InlineKeyboardButton("🏷 Статус", callback_data=f"{CB_EMP_STATUS_PREFIX}{user_id}"),
                InlineKeyboardButton("📝 Комментарий", callback_data=f"{CB_EMP_COMMENT_PREFIX}{user_id}"),
            ],
            [
                InlineKeyboardButton("📆 Смены", callback_data=f"{CB_EMP_SHIFTS_PREFIX}{user_id}"),
                InlineKeyboardButton("🚕 Такси", callback_data=f"{CB_EMP_TAXI_PREFIX}{user_id}"),
            ],
            [
                InlineKeyboardButton("📋 Отчёты", callback_data=f"{CB_EMP_REPORTS_PREFIX}{user_id}"),
                InlineKeyboardButton("✅ Чек-листы", callback_data=f"{CB_EMP_CHECKLISTS_PREFIX}{user_id}"),
            ],
            [
                InlineKeyboardButton("📊 XLSX-отчёт", callback_data=f"{CB_EMP_XLSX_ONE_PREFIX}{user_id}")
            ],
            [
                InlineKeyboardButton("🗑 Удалить сотрудника", callback_data=CB_EMP_DELETE)
            ],
            [
                InlineKeyboardButton("◀️ Назад", callback_data=CB_EMP_BACK)
            ],
        ]
    )


def confirm_delete_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🗑 Удалить полностью",
                    callback_data=f"{CB_EMP_DELETE_HARD}:{user_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🙈 Скрыть из списка (данные сохранятся)",
                    callback_data=f"{CB_EMP_DELETE_SOFT}:{user_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "❌ Отмена",
                    callback_data=f"{CB_EMP_DETAIL_PREFIX}{user_id}",
                ),
            ],
        ]
    )


def edit_status_keyboard(user_id: int) -> InlineKeyboardMarkup:
    rows = []
    for status in STATUSES:
        rows.append(
            [
                InlineKeyboardButton(
                    status,
                    callback_data=f"{CB_EMP_SET_STATUS_PREFIX}{user_id}:{status}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton("✖️ Отмена", callback_data=CB_EMP_CANCEL)
        ]
    )
    return InlineKeyboardMarkup(rows)


def taxi_photos_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📸 Отправить фото такси", callback_data=f"{CB_EMP_TAXI_PHOTOS_PREFIX}{user_id}")
            ],
            [
                InlineKeyboardButton("◀️ Назад", callback_data=f"{CB_EMP_DETAIL_PREFIX}{user_id}")
            ],
        ]
    )


def analytics_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📥 Скачать XLSX", callback_data=CB_EMP_XLSX_ALL)
            ],
            [
                InlineKeyboardButton("◀️ Назад", callback_data=CB_EMP_HOME)
            ],
        ]
    )


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✖️ Отмена", callback_data=CB_EMP_CANCEL)
            ]
        ]
    )