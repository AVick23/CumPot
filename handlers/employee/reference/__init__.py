from telegram.ext import CallbackQueryHandler, MessageHandler, filters
from .handlers import (
    show_reference_main,
    reference_callback,
    reference_text_input,
    prompt_search,
)
from .constants import (
    REFERENCE_MAIN,
    REFERENCE_CATEGORY,
    REFERENCE_LIST,
    REFERENCE_DETAIL,
    REFERENCE_SEARCH_INPUT,
    REFERENCE_SEARCH_RESULTS,
    REFERENCE_SHELF_LIFE,
    CB_REF_SEARCH,
)


def register_reference_states(states: dict):
    """Регистрирует состояния справочника."""
    # Главное меню
    states[REFERENCE_MAIN] = [
        CallbackQueryHandler(reference_callback),
    ]

    # Категории
    states[REFERENCE_CATEGORY] = [
        CallbackQueryHandler(reference_callback),
    ]

    # Список рецептов
    states[REFERENCE_LIST] = [
        CallbackQueryHandler(reference_callback),
    ]

    # Деталь рецепта
    states[REFERENCE_DETAIL] = [
        CallbackQueryHandler(reference_callback),
    ]

    # Ожидание поискового запроса
    states[REFERENCE_SEARCH_INPUT] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, reference_text_input),
        CallbackQueryHandler(reference_callback),
    ]

    # Результаты поиска
    states[REFERENCE_SEARCH_RESULTS] = [
        CallbackQueryHandler(reference_callback),
    ]

    # Сроки годности
    states[REFERENCE_SHELF_LIFE] = [
        CallbackQueryHandler(reference_callback),
    ]


# Загружаем данные при импорте модуля
from .handlers import load_recipes_from_excel
load_recipes_from_excel()