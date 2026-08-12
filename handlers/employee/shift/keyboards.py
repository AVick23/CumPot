from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Клавиатура для управления сменой (если потребуется)
def shift_control_keyboard(has_shift: bool) -> InlineKeyboardMarkup:
    if has_shift:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⏹ Завершить смену", callback_data="shift_end")]
        ])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Начать смену", callback_data="shift_start")]
    ])