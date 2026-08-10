from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes, ConversationHandler
from .constant import *
from .keyboards import *
from .utils import *
from db.users import get_user
from datetime import datetime

async def start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    shift = get_active_shift(user_id)
    text = f"👋 Привет, {user.first_name}!"
    if shift:
        text += f"\nТы на смене ({shift['location']}). Выбери действие:"
    else:
        text += "\nДля доступа к чек-листам сначала отметься на смене."
    await update.message.reply_text(
        text,
        reply_markup=main_menu_keyboard(has_shift=bool(shift))
    )
    return MAIN_MENU

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == CB_SHIFT_MARK:
        shift = get_active_shift(user_id)
        if shift:
            await query.answer("Вы уже на смене!", show_alert=True)
            return MAIN_MENU
        else:
            await query.edit_message_text(
                "Выбери локацию:",
                reply_markup=location_keyboard()
            )
            return SELECT_LOCATION

    elif data == CB_CHECKLIST:
        # Кнопка видна только если есть смена, но проверка на всякий случай
        shift = get_active_shift(user_id)
        if not shift:
            await query.answer("Сначала отметься на смене!", show_alert=True)
            return MAIN_MENU
        items = get_checklist_items(user_id)
        if items is None:
            await query.edit_message_text(
                "Ошибка получения чек-листа. Попробуйте позже.",
                reply_markup=main_menu_keyboard(has_shift=True)
            )
            return MAIN_MENU
        if not items:
            await query.edit_message_text(
                "На сегодня нет задач.",
                reply_markup=main_menu_keyboard(has_shift=True)
            )
            return MAIN_MENU
        await query.edit_message_text(
            "Ваш чек-лист на сегодня:",
            reply_markup=checklist_keyboard(items, datetime.now().strftime("%Y-%m-%d"))
        )
        return CHECKLIST_VIEW

    elif data == CB_PROGRESS:
        shift = get_active_shift(user_id)
        if not shift:
            await query.answer("Сначала отметься на смене!", show_alert=True)
            return MAIN_MENU
        done, total, items = get_user_progress_summary(user_id)
        if done is None:
            await query.edit_message_text(
                "Ошибка получения прогресса.",
                reply_markup=main_menu_keyboard(has_shift=True)
            )
            return MAIN_MENU
        progress_text = f"📊 Твой прогресс: {done}/{total} выполнено ({int(done/total*100)}%)\n\n"
        if done < total:
            undone = [item for item in items if not item['completed']]
            progress_text += "❌ Осталось:\n" + "\n".join([f"- {item['text']}" for item in undone[:10]])
            if len(undone) > 10:
                progress_text += f"\n...и ещё {len(undone)-10} пунктов"
        else:
            progress_text += "🎉 Все задачи выполнены!"
        await query.edit_message_text(
            progress_text,
            reply_markup=progress_keyboard()
        )
        return PROGRESS_VIEW

    elif data == CB_BACK_MAIN:
        shift = get_active_shift(user_id)
        await query.edit_message_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(has_shift=bool(shift))
        )
        return MAIN_MENU

    else:
        await query.edit_message_text("Неизвестная команда", reply_markup=main_menu_keyboard(has_shift=bool(get_active_shift(user_id))))
        return MAIN_MENU

async def location_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == CB_SHIFT_BAR:
        mark_shift(user_id, "bar")
        await query.edit_message_text(
            "✅ Ты отметился на баре! Теперь доступны чек-листы.",
            reply_markup=main_menu_keyboard(has_shift=True)
        )
        return MAIN_MENU

    elif data == CB_SHIFT_KITCHEN:
        mark_shift(user_id, "kitchen")
        await query.edit_message_text(
            "✅ Ты отметился на кухне! Теперь доступны чек-листы.",
            reply_markup=main_menu_keyboard(has_shift=True)
        )
        return MAIN_MENU

    elif data == CB_BACK_MAIN:
        shift = get_active_shift(user_id)
        await query.edit_message_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(has_shift=bool(shift))
        )
        return MAIN_MENU

    else:
        await query.edit_message_text("Неизвестная локация", reply_markup=location_keyboard())
        return SELECT_LOCATION

async def checklist_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith(CB_ITEM_DONE):
        item_id = int(data.split("_")[-1])
        mark_item_done(user_id, item_id)
        items = get_checklist_items(user_id)
        if items:
            await query.edit_message_text(
                "Ваш чек-лист обновлён:",
                reply_markup=checklist_keyboard(items, datetime.now().strftime("%Y-%m-%d"))
            )
        else:
            await query.edit_message_text(
                "Чек-лист пуст.",
                reply_markup=main_menu_keyboard(has_shift=True)
            )
            return MAIN_MENU
        return CHECKLIST_VIEW

    elif data.startswith(CB_ITEM_UNDO):
        item_id = int(data.split("_")[-1])
        mark_item_undone(user_id, item_id)
        items = get_checklist_items(user_id)
        if items:
            await query.edit_message_text(
                "Ваш чек-лист обновлён:",
                reply_markup=checklist_keyboard(items, datetime.now().strftime("%Y-%m-%d"))
            )
        else:
            await query.edit_message_text(
                "Чек-лист пуст.",
                reply_markup=main_menu_keyboard(has_shift=True)
            )
            return MAIN_MENU
        return CHECKLIST_VIEW

    elif data == CB_BACK_MAIN:
        shift = get_active_shift(user_id)
        await query.edit_message_text(
            "Главное меню:",
            reply_markup=main_menu_keyboard(has_shift=bool(shift))
        )
        return MAIN_MENU

    else:
        await query.edit_message_text("Неизвестное действие", reply_markup=main_menu_keyboard(has_shift=True))
        return MAIN_MENU

async def progress_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    shift = get_active_shift(user_id)
    await query.edit_message_text(
        "Главное меню:",
        reply_markup=main_menu_keyboard(has_shift=bool(shift))
    )
    return MAIN_MENU

# Заглушка для заголовков категорий
async def noop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Это просто заголовок")