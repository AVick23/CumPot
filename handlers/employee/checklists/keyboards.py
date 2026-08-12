from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .constants import (
    CATEGORY_NAMES,
    CATEGORY_ORDER,
    CB_CATEGORY_PREFIX,
    CB_ITEM_PREFIX,
    CB_TOGGLE_PREFIX,
    CB_PHOTO_PREFIX,
    CB_VIEW_PHOTO_PREFIX,
    CB_PHOTO_CANCEL,
    CB_BACK_MENU,
    CB_BACK_CATEGORIES,
)


def _clip(text: str | None, limit: int = 35) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + "…"


def categories_keyboard(stats: dict[str, dict]) -> InlineKeyboardMarkup:
    rows = []
    for cat in CATEGORY_ORDER:
        if cat not in stats:
            continue
        item = stats[cat]
        if item.get("total", 0) <= 0:
            continue
        label = f"{CATEGORY_NAMES.get(cat, cat)} · {item['done']}/{item['total']}"
        rows.append([
            InlineKeyboardButton(label, callback_data=f"{CB_CATEGORY_PREFIX}{cat}")
        ])
    rows.append([InlineKeyboardButton("◀️ В меню", callback_data=CB_BACK_MENU)])
    return InlineKeyboardMarkup(rows)


def checklist_keyboard(items: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for item in items:
        status = "✅" if item.get("completed") else "⚪️"
        photo = "🖼" if item.get("has_photo") else ""
        label = f"{status}{photo} {_clip(item.get('text'), 33)}"
        rows.append([
            InlineKeyboardButton(label, callback_data=f"{CB_ITEM_PREFIX}{item['id']}")
        ])
    rows.append([
        InlineKeyboardButton("◀️ Категории", callback_data=CB_BACK_CATEGORIES),
        InlineKeyboardButton("🏠 Меню", callback_data=CB_BACK_MENU),
    ])
    return InlineKeyboardMarkup(rows)


def item_detail_keyboard(item_id: int, is_completed: bool, has_photo: bool = False) -> InlineKeyboardMarkup:
    rows = []

    if not is_completed:
        rows.append([
            InlineKeyboardButton("✅ Выполнить", callback_data=f"{CB_TOGGLE_PREFIX}{item_id}")
        ])
        rows.append([
            InlineKeyboardButton("📷 Выполнить с фото", callback_data=f"{CB_PHOTO_PREFIX}{item_id}")
        ])
    else:
        rows.append([
            InlineKeyboardButton("↩️ Отменить", callback_data=f"{CB_TOGGLE_PREFIX}{item_id}")
        ])
        photo_label = "📷 Заменить фото" if has_photo else "📷 Прикрепить фото"
        rows.append([
            InlineKeyboardButton(photo_label, callback_data=f"{CB_PHOTO_PREFIX}{item_id}")
        ])

    if has_photo:
        rows.append([
            InlineKeyboardButton("👁 Посмотреть фото", callback_data=f"{CB_VIEW_PHOTO_PREFIX}{item_id}")
        ])

    rows.append([
        InlineKeyboardButton("◀️ К списку", callback_data=CB_BACK_CATEGORIES)
    ])

    return InlineKeyboardMarkup(rows)


def progress_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ В меню", callback_data=CB_BACK_MENU)]
    ])


def photo_prompt_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✖️ Отмена", callback_data=CB_PHOTO_CANCEL)]
    ])