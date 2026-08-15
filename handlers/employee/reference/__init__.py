from telegram.ext import CallbackQueryHandler, MessageHandler, filters

from .handlers import (
    show_reference_main,
    reference_callback,
    reference_text_input,
    prompt_search,
    load_recipes_from_excel,
)

from .constants import (
    REFERENCE_MAIN,
    REFERENCE_CATEGORY,
    REFERENCE_LIST,
    REFERENCE_DETAIL,
    REFERENCE_SEARCH_INPUT,
    REFERENCE_SEARCH_RESULTS,
    REFERENCE_SHELF_LIFE,
    REFERENCE_BASE,
    REFERENCE_SEASON,
)


def register_reference_states(states: dict):
    states[REFERENCE_MAIN] = [CallbackQueryHandler(reference_callback)]
    states[REFERENCE_BASE] = [CallbackQueryHandler(reference_callback)]
    states[REFERENCE_SEASON] = [CallbackQueryHandler(reference_callback)]
    states[REFERENCE_CATEGORY] = [CallbackQueryHandler(reference_callback)]
    states[REFERENCE_LIST] = [CallbackQueryHandler(reference_callback)]
    states[REFERENCE_DETAIL] = [CallbackQueryHandler(reference_callback)]
    states[REFERENCE_SEARCH_INPUT] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, reference_text_input),
        CallbackQueryHandler(reference_callback),
    ]
    states[REFERENCE_SEARCH_RESULTS] = [CallbackQueryHandler(reference_callback)]
    states[REFERENCE_SHELF_LIFE] = [CallbackQueryHandler(reference_callback)]


load_recipes_from_excel()