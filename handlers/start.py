from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db.users import save_user, get_user

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    tg_id = user.id

    # Сохраняем пользователя в БД
    save_user(tg_id, user.username, user.first_name, user.last_name)
    user_data = get_user(tg_id)

    # Проверяем, админ ли он
    if user_data["is_admin"]:
        text = "👋 Привет, Администратор!\nЗдесь будет меню управления."
        keyboard = [
            [InlineKeyboardButton("📋 Смены сегодня", callback_data="admin_shifts")],
            [InlineKeyboardButton("📊 Прогресс сотрудников", callback_data="admin_progress")],
            [InlineKeyboardButton("⚙️ Редактор чек-листов", callback_data="admin_edit")],
        ]
    else:
        text = f"👋 Привет, {user.first_name}!\nТы сотрудник. Отметься на смене, чтобы получить доступ к чек-листам."
        keyboard = [
            [InlineKeyboardButton("✅ Отметиться на смене", callback_data="shift_mark")],
            [InlineKeyboardButton("📋 Мои чек-листы", callback_data="checklist")],
            [InlineKeyboardButton("📈 Мой прогресс", callback_data="progress")],
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup)