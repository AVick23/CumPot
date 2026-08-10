from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from .constant import *
from .keyboards import *
from .utils import *
from db.users import get_user

# Вспомогательная функция для безопасного редактирования
async def safe_edit(query, text, reply_markup=None):
    try:
        await query.edit_message_text(text, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            await query.answer("Уже отображено", show_alert=False)
        else:
            raise e

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Привет, Администратор {user.first_name}!",
        reply_markup=admin_main_keyboard()
    )
    return ADMIN_MAIN

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == CB_ADMIN_SHIFTS:
        shifts = get_today_shifts()
        if shifts:
            text = "📋 Смены сегодня:\n"
            for s in shifts:
                text += f"- {s['first_name']} {s['last_name']} ({s['location']}) с {s['start_time']}\n"
        else:
            text = "Сегодня никто не отметился."
        await safe_edit(query, text, reply_markup=admin_back_keyboard())
        return ADMIN_SHIFTS
    elif data == CB_ADMIN_PROGRESS:
        await safe_edit(query, "Здесь будет просмотр прогресса сотрудников (в разработке).", reply_markup=admin_back_keyboard())
        return ADMIN_PROGRESS
    elif data == CB_ADMIN_EDIT:
        await safe_edit(query, "Редактор чек-листов (в разработке).", reply_markup=admin_back_keyboard())
        return ADMIN_EDIT
    elif data == CB_ADMIN_BACK:
        await safe_edit(query, "Главное меню админа:", reply_markup=admin_main_keyboard())
        return ADMIN_MAIN
    else:
        await safe_edit(query, "Неизвестная команда", reply_markup=admin_main_keyboard())
        return ADMIN_MAIN