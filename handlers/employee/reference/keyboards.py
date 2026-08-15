from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .constants import (
    CB_REF_CATEGORY_PREFIX,
    CB_REF_ITEM_PREFIX,
    CB_REF_SEARCH,
    CB_REF_BACK,
    CB_REF_HOME,
    CB_REF_SHELF_LIFE,
    CB_REF_PAGE_PREFIX,
    CB_REF_SEARCH_PAGE_PREFIX,
    CB_REF_BACK_TO_LIST,
)


def _clip(text: str, limit: int = 35) -> str:
    text = " ".join((text or "").split())

    if len(text) <= limit:
        return text

    return text[: limit - 1].rstrip() + "…"


def _pagination_row(
    page: int,
    total_pages: int,
    prefix: str,
) -> list[InlineKeyboardButton]:
    row = []

    if page > 1:
        row.append(
            InlineKeyboardButton(
                "←",
                callback_data=f"{prefix}{page - 1}",
            )
        )

    row.append(
        InlineKeyboardButton(
            f"{page}/{total_pages}",
            callback_data="noop",
        )
    )

    if page < total_pages:
        row.append(
            InlineKeyboardButton(
                "→",
                callback_data=f"{prefix}{page + 1}",
            )
        )

    return row


def reference_main_keyboard() -> InlineKeyboardMarkup:
    """
    Главное меню справочника.
    """
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔍 Поиск",
                    callback_data=CB_REF_SEARCH,
                )
            ],
            [
                InlineKeyboardButton(
                    "📂 Категории",
                    callback_data=f"{CB_REF_CATEGORY_PREFIX}all",
                )
            ],
            [
                InlineKeyboardButton(
                    "📅 Сроки годности",
                    callback_data=CB_REF_SHELF_LIFE,
                )
            ],
            [
                InlineKeyboardButton(
                    "🏠 Главное меню",
                    callback_data=CB_REF_BACK,
                )
            ],
        ]
    )


def categories_keyboard(category_counts: dict[str, int]) -> InlineKeyboardMarkup:
    """
    Клавиатура категорий с количеством рецептов.
    """
    rows = []

    for category in sorted(category_counts.keys()):
        count = category_counts.get(category, 0)

        rows.append(
            [
                InlineKeyboardButton(
                    f"{category} · {count}",
                    callback_data=f"{CB_REF_CATEGORY_PREFIX}{category}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                "🏠 Меню справочника",
                callback_data=CB_REF_HOME,
            )
        ]
    )

    return InlineKeyboardMarkup(rows)


def items_list_keyboard(
    items: list,
    category: str,
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    """
    Клавиатура списка рецептов в категории.
    """
    rows = []

    for item in items:
        rows.append(
            [
                InlineKeyboardButton(
                    _clip(item.name, 34),
                    callback_data=f"{CB_REF_ITEM_PREFIX}{item.id}",
                )
            ]
        )

    if total_pages > 1:
        rows.append(
            _pagination_row(
                page=page,
                total_pages=total_pages,
                prefix=CB_REF_PAGE_PREFIX,
            )
        )

    rows.append(
        [
            InlineKeyboardButton(
                "📂 Категории",
                callback_data=f"{CB_REF_CATEGORY_PREFIX}all",
            ),
            InlineKeyboardButton(
                "🏠 Меню",
                callback_data=CB_REF_HOME,
            ),
        ]
    )

    return InlineKeyboardMarkup(rows)


def search_results_keyboard(
    items: list,
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    """
    Клавиатура результатов поиска.
    """
    rows = []

    for item in items:
        rows.append(
            [
                InlineKeyboardButton(
                    _clip(item.name, 34),
                    callback_data=f"{CB_REF_ITEM_PREFIX}{item.id}",
                )
            ]
        )

    if total_pages > 1:
        rows.append(
            _pagination_row(
                page=page,
                total_pages=total_pages,
                prefix=CB_REF_SEARCH_PAGE_PREFIX,
            )
        )

    rows.append(
        [
            InlineKeyboardButton(
                "🔍 Новый поиск",
                callback_data=CB_REF_SEARCH,
            ),
            InlineKeyboardButton(
                "🏠 Меню",
                callback_data=CB_REF_HOME,
            ),
        ]
    )

    return InlineKeyboardMarkup(rows)


def item_detail_keyboard(recipe) -> InlineKeyboardMarkup:
    """
    Клавиатура карточки рецепта.
    """
    category = recipe.category or "Рецепты"

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "◀️ Назад",
                    callback_data=CB_REF_BACK_TO_LIST,
                )
            ],
            [
                InlineKeyboardButton(
                    _clip(f"📂 {category}", 26),
                    callback_data=f"{CB_REF_CATEGORY_PREFIX}{category}",
                ),
                InlineKeyboardButton(
                    "🔍 Поиск",
                    callback_data=CB_REF_SEARCH,
                ),
            ],
            [
                InlineKeyboardButton(
                    "🏠 Меню справочника",
                    callback_data=CB_REF_HOME,
                )
            ],
        ]
    )


def search_prompt_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура при ожидании поискового запроса.
    """
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✖️ Отмена",
                    callback_data=CB_REF_HOME,
                )
            ]
        ]
    )


def shelf_life_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для раздела сроков годности.
    """
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🏠 Меню справочника",
                    callback_data=CB_REF_HOME,
                )
            ]
        ]
    )