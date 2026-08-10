from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes, ConversationHandler
from telegram.error import BadRequest
from .constants import *
from .keyboards import *
from .utils import *
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def safe_edit(query, text, reply_markup=None):
    try:
        await query.edit_message_text(text, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            await query.answer("Уже отображено", show_alert=False)
        else:
            raise e

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
            await safe_edit(query, "Выбери локацию:", reply_markup=location_keyboard())
            return SELECT_LOCATION

    elif data == CB_CHECKLIST:
        shift = get_active_shift(user_id)
        if not shift:
            await query.answer("Сначала отметься на смене!", show_alert=True)
            return MAIN_MENU
        all_items = get_checklist_items(user_id, context)
        if all_items is None:
            await safe_edit(query, "Ошибка получения чек-листа.", reply_markup=main_menu_keyboard(has_shift=True))
            return MAIN_MENU
        cats = list({item['category'] for item in all_items})
        if not cats:
            await safe_edit(query, "На сегодня нет задач.", reply_markup=main_menu_keyboard(has_shift=True))
            return MAIN_MENU
        context.user_data.pop('current_category', None)
        await safe_edit(query, "📋 Выбери категорию:", reply_markup=categories_keyboard(cats))
        return CATEGORY_SELECT

    elif data == CB_PROGRESS:
        shift = get_active_shift(user_id)
        if not shift:
            await query.answer("Сначала отметься на смене!", show_alert=True)
            return MAIN_MENU
        done, total, items, categories = get_user_progress_summary(user_id, context)
        if done is None:
            await safe_edit(query, "Ошибка получения прогресса.", reply_markup=main_menu_keyboard(has_shift=True))
            return MAIN_MENU
        progress_text = f"📊 Твой прогресс: {done}/{total} выполнено ({int(done/total*100) if total else 0}%)\n\n"
        for cat, stats in categories.items():
            cat_name = CATEGORY_NAMES.get(cat, cat)
            progress_text += f"• {cat_name}: {stats['done']}/{stats['total']}\n"
        if done < total:
            undone = [item for item in items if not item['completed']]
            progress_text += "\n❌ Осталось:\n" + "\n".join([f"- {item['text']}" for item in undone[:10]])
            if len(undone) > 10:
                progress_text += f"\n...и ещё {len(undone)-10} пунктов"
        else:
            progress_text += "\n🎉 Все задачи выполнены!"
        await safe_edit(query, progress_text, reply_markup=progress_keyboard())
        return PROGRESS_VIEW

    elif data == CB_BACK_MAIN:
        # Возврат в главное меню из любого места (корневой выход)
        shift = get_active_shift(user_id)
        context.user_data.pop('current_category', None)
        await safe_edit(query, "Главное меню:", reply_markup=main_menu_keyboard(has_shift=bool(shift)))
        return MAIN_MENU

    else:
        await safe_edit(query, "Неизвестная команда", reply_markup=main_menu_keyboard(has_shift=bool(get_active_shift(user_id))))
        return MAIN_MENU

async def category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith(CB_CATEGORY):
        category = data.split("_")[1]
        context.user_data['current_category'] = category
        items = get_items_by_category(user_id, context, category)
        if not items:
            cats = list({item['category'] for item in get_checklist_items(user_id, context) or []})
            await safe_edit(query, "В этой категории нет задач.", reply_markup=categories_keyboard(cats))
            return CATEGORY_SELECT
        await safe_edit(query, f"📋 {CATEGORY_NAMES.get(category, category)}:\nНажми на задачу для подробностей.", reply_markup=checklist_keyboard(items))
        return CHECKLIST_VIEW

    elif data == CB_BACK_MAIN:
        shift = get_active_shift(user_id)
        context.user_data.pop('current_category', None)
        await safe_edit(query, "Главное меню:", reply_markup=main_menu_keyboard(has_shift=bool(shift)))
        return MAIN_MENU

    else:
        await safe_edit(query, "Неизвестный выбор", reply_markup=main_menu_keyboard(has_shift=bool(get_active_shift(user_id))))
        return MAIN_MENU

async def view_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith(CB_ITEM_VIEW):
        item_id = int(data.split("_")[-1])
        item = get_item_by_id(user_id, item_id, context)
        if not item:
            await safe_edit(query, "Задача не найдена.", reply_markup=main_menu_keyboard(has_shift=True))
            return MAIN_MENU
        status_text = "✅ Выполнено" if item['completed'] else "⬜ Не выполнено"
        text = f"📌 {item['text']}\n\n"
        text += f"Статус: {status_text}\n"
        text += f"Категория: {CATEGORY_NAMES.get(item['category'], item['category'])}\n"
        if item['type'] == 'weekly':
            text += "Тип: недельная задача"
        else:
            text += "Тип: ежедневная задача"
        await safe_edit(query, text, reply_markup=item_detail_keyboard(item_id, item['completed']))
        return ITEM_DETAIL

    elif data == CB_BACK_CATEGORIES:
        # Возврат к выбору категорий
        user_id = query.from_user.id
        all_items = get_checklist_items(user_id, context)
        cats = list({item['category'] for item in all_items}) if all_items else []
        await safe_edit(query, "📋 Выбери категорию:", reply_markup=categories_keyboard(cats))
        return CATEGORY_SELECT

    else:
        await safe_edit(query, "Неизвестное действие", reply_markup=main_menu_keyboard(has_shift=True))
        return MAIN_MENU

async def toggle_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith(CB_ITEM_TOGGLE):
        item_id = int(data.split("_")[-1])
        item = get_item_by_id(user_id, item_id, context)
        if not item:
            await safe_edit(query, "Задача не найдена.", reply_markup=main_menu_keyboard(has_shift=True))
            return MAIN_MENU
        if item['completed']:
            changed = mark_item_undone(user_id, item_id, context)
            if changed:
                await query.answer("Задача отменена")
            else:
                await query.answer("Уже не выполнено")
        else:
            changed = mark_item_done(user_id, item_id, context)
            if changed:
                await query.answer("Задача выполнена! 🎉")
            else:
                await query.answer("Уже выполнено")
        updated_item = get_item_by_id(user_id, item_id, context)
        status_text = "✅ Выполнено" if updated_item['completed'] else "⬜ Не выполнено"
        text = f"📌 {updated_item['text']}\n\n"
        text += f"Статус: {status_text}\n"
        text += f"Категория: {CATEGORY_NAMES.get(updated_item['category'], updated_item['category'])}\n"
        if updated_item['type'] == 'weekly':
            text += "Тип: недельная задача"
        else:
            text += "Тип: ежедневная задача"
        await safe_edit(query, text, reply_markup=item_detail_keyboard(item_id, updated_item['completed']))
        return ITEM_DETAIL

    elif data == CB_BACK_MAIN:
        shift = get_active_shift(user_id)
        context.user_data.pop('current_category', None)
        await safe_edit(query, "Главное меню:", reply_markup=main_menu_keyboard(has_shift=bool(shift)))
        return MAIN_MENU

    else:
        await safe_edit(query, "Неизвестное действие", reply_markup=main_menu_keyboard(has_shift=True))
        return MAIN_MENU

async def back_to_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат к списку задач текущей категории"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    category = context.user_data.get('current_category')
    if category:
        items = get_items_by_category(user_id, context, category)
        if items:
            await safe_edit(query, f"📋 {CATEGORY_NAMES.get(category, category)}:\nНажми на задачу для подробностей.", reply_markup=checklist_keyboard(items))
            return CHECKLIST_VIEW
    # Если категория не сохранена, идём к выбору категорий
    all_items = get_checklist_items(user_id, context)
    cats = list({item['category'] for item in all_items}) if all_items else []
    await safe_edit(query, "📋 Выбери категорию:", reply_markup=categories_keyboard(cats))
    return CATEGORY_SELECT

async def location_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == CB_SHIFT_BAR:
        mark_shift(user_id, "bar")
        await safe_edit(query, "✅ Ты отметился на баре! Теперь доступны чек-листы.", reply_markup=main_menu_keyboard(has_shift=True))
        return MAIN_MENU

    elif data == CB_SHIFT_KITCHEN:
        mark_shift(user_id, "kitchen")
        await safe_edit(query, "✅ Ты отметился на кухне! Теперь доступны чек-листы.", reply_markup=main_menu_keyboard(has_shift=True))
        return MAIN_MENU

    elif data == CB_BACK_MAIN:
        shift = get_active_shift(user_id)
        context.user_data.pop('current_category', None)
        await safe_edit(query, "Главное меню:", reply_markup=main_menu_keyboard(has_shift=bool(shift)))
        return MAIN_MENU

    else:
        await safe_edit(query, "Неизвестная локация", reply_markup=location_keyboard())
        return SELECT_LOCATION

async def progress_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    shift = get_active_shift(user_id)
    context.user_data.pop('current_category', None)
    await safe_edit(query, "Главное меню:", reply_markup=main_menu_keyboard(has_shift=bool(shift)))
    return MAIN_MENU

async def noop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Это просто заголовок")