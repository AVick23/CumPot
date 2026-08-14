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
    Клавиатура просмотра профиля – каждая кнопка ведёт к редактированию поля.
    Показывает текущее значение (обрезанное для компактности).
    """
    buttons = []
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
        current = user_data.get(field) or "—"
        # Обрезаем длинные значения
        if len(current) > 30:
            current = current[:27] + "…"
        button_text = f"{label}  {current}"
        buttons.append([InlineKeyboardButton(button_text, callback_data=callback)])

    # Кнопка выхода в главное меню
    buttons.append([InlineKeyboardButton("🏠 Назад в меню", callback_data=CB_PROFILE_BACK)])
    return InlineKeyboardMarkup(buttons)


def profile_edit_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура во время редактирования – только кнопка отмены."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Отмена", callback_data=CB_PROFILE_CANCEL)]
    ])