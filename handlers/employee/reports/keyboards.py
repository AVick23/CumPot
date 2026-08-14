from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .constants import (
    CB_REPORT_BACK_MENU,
    CB_REPORT_OPEN_PREFIX,
    CB_REPORT_SAVE,
    CB_REPORT_TEXT_MODE,
    CB_REPORT_LOAD_LAST,
    CB_REPORT_CLEAR,
    CB_REPORT_SECTION_MODE,
    CB_REPORT_CANCEL,
    CB_REPORT_BACK_EDITOR,
    CB_REPORT_SECTION_MENU_CLEAR,
    CB_REPORT_SECTION_START,
    CB_REPORT_SECTION_CHOOSE,
    CB_REPORT_SECTION_PREFIX,
    CB_REPORT_SECTION_DONE,
    CB_REPORT_SECTION_SKIP,
    CB_REPORT_SECTION_EXIT,
)


def report_home_keyboard(
    opening_exists: bool,
    closing_exists: bool,
) -> InlineKeyboardMarkup:
    opening_label = f"{'✅' if opening_exists else '⚪️'} 📋 Открытие"
    closing_label = f"{'✅' if closing_exists else '⚪️'} 🌙 Закрытие"

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    opening_label,
                    callback_data=f"{CB_REPORT_OPEN_PREFIX}opening",
                )
            ],
            [
                InlineKeyboardButton(
                    closing_label,
                    callback_data=f"{CB_REPORT_OPEN_PREFIX}closing",
                )
            ],
            [
                InlineKeyboardButton("🏠 Меню", callback_data=CB_REPORT_BACK_MENU)
            ],
        ]
    )


def report_editor_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Сохранить", callback_data=CB_REPORT_SAVE)
            ],
            [
                InlineKeyboardButton("🧾 Текстом", callback_data=CB_REPORT_TEXT_MODE),
                InlineKeyboardButton("📋 Последний", callback_data=CB_REPORT_LOAD_LAST),
            ],
            [
                InlineKeyboardButton("🗑 Очистить", callback_data=CB_REPORT_CLEAR),
                InlineKeyboardButton("🧩 По пунктам", callback_data=CB_REPORT_SECTION_MODE),
            ],
            [
                InlineKeyboardButton("✖️ Отмена", callback_data=CB_REPORT_CANCEL)
            ],
        ]
    )


def section_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🗑 Очистить весь отчёт",
                    callback_data=CB_REPORT_SECTION_MENU_CLEAR,
                )
            ],
            [
                InlineKeyboardButton(
                    "🚀 Заполнить с нуля",
                    callback_data=CB_REPORT_SECTION_START,
                )
            ],
            [
                InlineKeyboardButton(
                    "✏️ Выбрать пункт",
                    callback_data=CB_REPORT_SECTION_CHOOSE,
                )
            ],
            [
                InlineKeyboardButton(
                    "◀️ Назад",
                    callback_data=CB_REPORT_BACK_EDITOR,
                )
            ],
        ]
    )


def section_list_keyboard(values: dict, sections: list[str]) -> InlineKeyboardMarkup:
    rows = []

    rows.append(
        [
            InlineKeyboardButton("✅ Готово", callback_data=CB_REPORT_SECTION_DONE)
        ]
    )

    for index, section in enumerate(sections):
        value = (values.get(section) or "").strip()
        icon = "✅" if value else "⚪️"

        rows.append(
            [
                InlineKeyboardButton(
                    f"{icon} {section}",
                    callback_data=f"{CB_REPORT_SECTION_PREFIX}{index}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton("◀️ Назад", callback_data=CB_REPORT_BACK_EDITOR)
        ]
    )

    return InlineKeyboardMarkup(rows)


def section_prompt_keyboard(guided: bool) -> InlineKeyboardMarkup:
    if guided:
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⏭ Пропустить",
                        callback_data=CB_REPORT_SECTION_SKIP,
                    )
                ],
                [
                    InlineKeyboardButton(
                        "✖️ Завершить",
                        callback_data=CB_REPORT_SECTION_EXIT,
                    )
                ],
            ]
        )

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🗑 Очистить пункт",
                    callback_data=CB_REPORT_SECTION_SKIP,
                )
            ],
            [
                InlineKeyboardButton(
                    "◀️ Назад",
                    callback_data=CB_REPORT_BACK_EDITOR,
                )
            ],
        ]
    )


def text_prompt_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("◀️ Назад", callback_data=CB_REPORT_BACK_EDITOR),
                InlineKeyboardButton("✖️ Отмена", callback_data=CB_REPORT_CANCEL),
            ]
        ]
    )