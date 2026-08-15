from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .constants import (
    CB_REFERENCE, CB_REF_CATEGORY_PREFIX, CB_REF_ITEM_PREFIX,
    CB_REF_SEARCH, CB_REF_BACK, CB_REF_HOME, CB_REF_SHELF_LIFE,
    CB_REF_PAGE_PREFIX, PAGE_SIZE,
)
from .search import get_categories

def _clip(text: str, limit: int = 35) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def reference_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню справочника."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Поиск по ключевым словам", callback_data=CB_REF_SEARCH)],
        [InlineKeyboardButton("📂 Категории", callback_data=f"{CB_REF_CATEGORY_PREFIX}all")],
        [InlineKeyboardButton("📋 Сроки годности", callback_data=CB_REF_SHELF_LIFE)],
        [InlineKeyboardButton("◀️ Назад в меню", callback_data=CB_REF_BACK)],
    ])


def categories_keyboard(categories: list[str]) -> InlineKeyboardMarkup:
    """Клавиатура со списком категорий."""
    rows = []
    for cat in sorted(categories):
        rows.append([
            InlineKeyboardButton(cat, callback_data=f"{CB_REF_CATEGORY_PREFIX}{cat}")
        ])
    rows.append([
        InlineKeyboardButton("◀️ Назад", callback_data=CB_REF_HOME)
    ])
    return InlineKeyboardMarkup(rows)


def items_list_keyboard(
    items: list,  # список Recipe
    category: str,
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    """Клавиатура для списка рецептов (с пагинацией)."""
    rows = []
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = items[start:end]

    for item in page_items:
        label = _clip(item.name, 30)
        rows.append([
            InlineKeyboardButton(label, callback_data=f"{CB_REF_ITEM_PREFIX}{item.id}")
        ])

    # Пагинация
    if total_pages > 1:
        nav_row = []
        if page > 1:
            nav_row.append(
                InlineKeyboardButton("◀️", callback_data=f"{CB_REF_PAGE_PREFIX}{page - 1}")
            )
        nav_row.append(
            InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop")
        )
        if page < total_pages:
            nav_row.append(
                InlineKeyboardButton("▶️", callback_data=f"{CB_REF_PAGE_PREFIX}{page + 1}")
            )
        rows.append(nav_row)

    rows.append([
        InlineKeyboardButton("◀️ Категории", callback_data=f"{CB_REF_CATEGORY_PREFIX}all"),
        InlineKeyboardButton("🏠 Меню", callback_data=CB_REF_BACK),
    ])
    return InlineKeyboardMarkup(rows)


def item_detail_keyboard(item_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для карточки рецепта."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад к списку", callback_data=CB_REF_HOME)],
        [InlineKeyboardButton("🏠 Меню", callback_data=CB_REF_BACK)],
    ])


def search_prompt_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура при ожидании ввода поискового запроса."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✖️ Отмена", callback_data=CB_REF_HOME)]
    ])


def shelf_life_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для возврата из раздела сроков годности."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад", callback_data=CB_REF_HOME)]
    ])