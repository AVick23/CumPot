from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .constants import (
    CATEGORY_NAMES,
    CATEGORY_ORDER,
    CB_CATEGORY_PREFIX,
    CB_ITEM_PREFIX,
    CB_TOGGLE_PREFIX,
    CB_PHOTO_ADD_PREFIX,
    CB_PHOTO_REPLACE_PREFIX,
    CB_VIEW_PHOTO_PREFIX,
    CB_PHOTO_CANCEL,
    CB_BACK_MENU,
    CB_BACK_CATEGORIES,
)


def _clip(text: str | None, limit: int = 35) -> str:
    text = " ".join((text or "").split())

    if len(text) <= limit:
        return text

    return text[: limit - 1].rstrip() + "…"


def categories_keyboard(stats: dict[str, dict]) -> InlineKeyboardMarkup:
    rows = []

    for cat in CATEGORY_ORDER:
        if cat not in stats:
            continue

        item = stats[cat]
        total = item.get("total", 0)
        done = item.get("done", 0)

        if total <= 0:
            continue

        if done == total:
            emoji = "✅"
        elif done > 0:
            emoji = "🕘"
        else:
            emoji = "⚪️"

        label = f"{emoji} {CATEGORY_NAMES.get(cat, cat)} · {done}/{total}"

        rows.append(
            [
                InlineKeyboardButton(
                    label,
                    callback_data=f"{CB_CATEGORY_PREFIX}{cat}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton("◀️ В меню", callback_data=CB_BACK_MENU)
        ]
    )

    return InlineKeyboardMarkup(rows)


def checklist_keyboard(items: list[dict]) -> InlineKeyboardMarkup:
    rows = []

    for item in items:
        completed = bool(item.get("completed"))
        requires_photo = bool(item.get("requires_photo"))
        photo_count = int(item.get("photo_count", 0) or 0)

        if completed:
            status = "✅"
        elif requires_photo:
            status = "📸"
        else:
            status = "⚪️"

        photo_badge = f"🖼{photo_count} " if photo_count > 0 else ""
        text = _clip(item.get("text"), 32)

        label = f"{status} {photo_badge}{text}".strip()

        rows.append(
            [
                InlineKeyboardButton(
                    label,
                    callback_data=f"{CB_ITEM_PREFIX}{item.get('id')}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton("◀️ Категории", callback_data=CB_BACK_CATEGORIES),
            InlineKeyboardButton("🏠 Меню", callback_data=CB_BACK_MENU),
        ]
    )

    return InlineKeyboardMarkup(rows)


def item_detail_keyboard(
    item_id: int,
    is_completed: bool,
    has_photo: bool = False,
    requires_photo: bool = False,
) -> InlineKeyboardMarkup:
    rows = []

    if not is_completed:
        if not requires_photo:
            rows.append(
                [
                    InlineKeyboardButton(
                        "✅ Выполнить",
                        callback_data=f"{CB_TOGGLE_PREFIX}{item_id}",
                    )
                ]
            )

        # Используем CB_PHOTO_ADD_PREFIX для выполнения с фото
        rows.append(
            [
                InlineKeyboardButton(
                    "📸 Выполнить с фото",
                    callback_data=f"{CB_PHOTO_ADD_PREFIX}{item_id}",
                )
            ]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton(
                    "↩️ Отменить",
                    callback_data=f"{CB_TOGGLE_PREFIX}{item_id}",
                )
            ]
        )

        if has_photo:
            # Если фото уже есть, две кнопки: добавить и заменить
            rows.append(
                [
                    InlineKeyboardButton(
                        "➕ Добавить фото",
                        callback_data=f"{CB_PHOTO_ADD_PREFIX}{item_id}",
                    ),
                    InlineKeyboardButton(
                        "📷 Заменить фото",
                        callback_data=f"{CB_PHOTO_REPLACE_PREFIX}{item_id}",
                    ),
                ]
            )
        else:
            # Если фото нет, одна кнопка прикрепить
            rows.append(
                [
                    InlineKeyboardButton(
                        "📷 Прикрепить фото",
                        callback_data=f"{CB_PHOTO_ADD_PREFIX}{item_id}",
                    )
                ]
            )

    if has_photo:
        rows.append(
            [
                InlineKeyboardButton(
                    "👁 Посмотреть фото",
                    callback_data=f"{CB_VIEW_PHOTO_PREFIX}{item_id}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton("◀️ К списку", callback_data=CB_BACK_CATEGORIES)
        ]
    )

    return InlineKeyboardMarkup(rows)


def progress_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("◀️ В меню", callback_data=CB_BACK_MENU)
            ]
        ]
    )


def photo_prompt_keyboard(has_photos: bool = False) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✖️ Отмена",
                    callback_data=CB_PHOTO_CANCEL,
                )
            ]
        ]
    )