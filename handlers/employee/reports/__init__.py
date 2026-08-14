from telegram.ext import CallbackQueryHandler, MessageHandler, filters

from .handlers import (
    show_reports_menu,
    report_callback,
    receive_report_text,
)

from .constants import (
    REPORT_SELECT_TYPE,
    REPORT_VIEW_DATE,
    REPORT_VIEW_DETAIL,
    REPORT_AWAIT_TEXT,
    REPORT_CONFIRM_SAVE,
)


def register_report_states(states: dict):
    """
    Регистрация состояний модуля отчётов сотрудника.
    """

    # Экраны с кнопками
    states[REPORT_SELECT_TYPE] = [
        CallbackQueryHandler(report_callback),
    ]

    states[REPORT_VIEW_DATE] = [
        CallbackQueryHandler(report_callback),
    ]

    states[REPORT_VIEW_DETAIL] = [
        CallbackQueryHandler(report_callback),
    ]

    # Ввод текста отчёта
    states[REPORT_AWAIT_TEXT] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_report_text),
        CallbackQueryHandler(report_callback),
    ]

    # Подтверждение сохранения.
    # Если пользователь вдруг отправит текст здесь — обновим черновик.
    states[REPORT_CONFIRM_SAVE] = [
        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_report_text),
        CallbackQueryHandler(report_callback),
    ]