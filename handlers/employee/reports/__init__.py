from telegram.ext import CallbackQueryHandler, MessageHandler, filters

from .handlers import (
    show_reports_menu,
    report_callback,
    receive_report_text,
)

from .constants import (
    REPORT_HOME,
    REPORT_EDITOR,
    REPORT_TEXT_MODE,
    REPORT_SECTION_MENU,
    REPORT_SECTION_LIST,
    REPORT_AWAIT_SECTION,
    REPORT_CALENDAR,
)


def register_report_states(states: dict):
    # Главный экран
    states[REPORT_HOME] = [
        CallbackQueryHandler(report_callback),
    ]

    # Редактор: сюда можно и писать текст, и нажимать кнопки
    states[REPORT_EDITOR] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_report_text),
        CallbackQueryHandler(report_callback),
    ]

    # Режим ввода полного текста
    states[REPORT_TEXT_MODE] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_report_text),
        CallbackQueryHandler(report_callback),
    ]

    # Меню "По пунктам"
    states[REPORT_SECTION_MENU] = [
        CallbackQueryHandler(report_callback),
    ]

    # Список пунктов
    states[REPORT_SECTION_LIST] = [
        CallbackQueryHandler(report_callback),
    ]

    # Ввод значения конкретного пункта
    states[REPORT_AWAIT_SECTION] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_report_text),
        CallbackQueryHandler(report_callback),
    ]

    # Календарь внутри редактора
    states[REPORT_CALENDAR] = [
        CallbackQueryHandler(report_callback),
    ]