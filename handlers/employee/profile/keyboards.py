from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from .constants import (
    CB_PROFILE_BACK,
    CB_PROFILE_EDIT_NAME,
    CB_PROFILE_EDIT_PHONE,
    CB_PROFILE_EDIT_BIRTHDAY,
    CB_PROFILE_EDIT_ADDRESS,
    CB_PROFILE_EDIT_RESPONSIBILITIES,
    CB_PROFILE_EDIT_POSITION,
    CB_PROFILE_CANCEL,
    FIELD_LABELS,
)


def profile_view_keyboard(user_data: dict) -> InlineKeyboardMarkup:
    """
    Клавиатура для просмотра профиля:
    кнопка для каждого поля, которое можно редактировать.
    """
    buttons = []

    # Поля, которые можно редактировать (порядок важен)
    editable_fields = [
        ("full_name", CB_PROFILE_EDIT_NAME),
        ("phone", CB_PROFILE_EDIT_PHONE),
        ("birthday", CB_PROFILE_EDIT_BIRTHDAY),
        ("address", CB_PROFILE_EDIT_ADDRESS),
        ("responsibilities", CB_PROFILE_EDIT_RESPONSIBILITIES),
        ("position", CB_PROFILE_EDIT_POSITION),
    ]

    for field, callback in editable_fields:
        label = FIELD_LABELS.get(field, field)
        current_value = user_data.get(field) or "—"
        # Обрезаем длинные значения для кнопки
        if len(current_value) > 30:
            current_value = current_value[:27] + "…"
        button_text = f"{label}: {current_value}"
        buttons.append([InlineKeyboardButton(button_text, callback_data=callback)])

    buttons.append([InlineKeyboardButton("◀️ Назад в меню", callback_data=CB_PROFILE_BACK)])
    return InlineKeyboardMarkup(buttons)


def profile_edit_keyboard(back_callback: str = CB_PROFILE_CANCEL) -> InlineKeyboardMarkup:
    """Клавиатура для отмены редактирования."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✖️ Отмена", callback_data=back_callback)]
    ])