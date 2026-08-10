from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes, ConversationHandler
from telegram.error import BadRequest
from .constants import *
from .keyboards import *
from .utils import *
from datetime import datetime

# Вспомогательная функция для безопасного редактирования сообщений
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
        if not all_items:
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
        progress_text = f"📊 Твой прогресс: {done}/{total} выполнено ({int(done/total*100)}%)\n\n"
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
        await safe_edit(query, f"📋 {CATEGORY_NAMES.get(category, category)}:", reply_markup=checklist_keyboard(items, category))
        return CHECKLIST_VIEW

    elif data == CB_BACK_MAIN:
        shift = get_active_shift(user_id)
        context.user_data.pop('current_category', None)
        await safe_edit(query, "Главное меню:", reply_markup=main_menu_keyboard(has_shift=bool(shift)))
        return MAIN_MENU

    else:
        await safe_edit(query, "Неизвестный выбор", reply_markup=main_menu_keyboard(has_shift=bool(get_active_shift(user_id))))
        return MAIN_MENU

async def checklist_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith(CB_ITEM_DONE):
        idx = int(data.split("_")[-1])
        changed = mark_item_done(user_id, idx, context)
        if not changed:
            await query.answer("Уже выполнено", show_alert=False)
            return CHECKLIST_VIEW
        current_category = context.user_data.get('current_category')
        if not current_category:
            all_items = get_checklist_items(user_id, context)
            cats = list({item['category'] for item in all_items}) if all_items else []
            await safe_edit(query, "Выбери категорию:", reply_markup=categories_keyboard(cats))
            return CATEGORY_SELECT
        items = get_items_by_category(user_id, context, current_category)
        if items:
            await safe_edit(query, f"📋 {CATEGORY_NAMES.get(current_category, current_category)}:", reply_markup=checklist_keyboard(items, current_category))
        else:
            all_items = get_checklist_items(user_id, context)
            cats = list({item['category'] for item in all_items}) if all_items else []
            await safe_edit(query, "Выбери категорию:", reply_markup=categories_keyboard(cats))
            return CATEGORY_SELECT
        return CHECKLIST_VIEW

    elif data.startswith(CB_ITEM_UNDO):
        idx = int(data.split("_")[-1])
        changed = mark_item_undone(user_id, idx, context)
        if not changed:
            await query.answer("Уже не выполнено", show_alert=False)
            return CHECKLIST_VIEW
        current_category = context.user_data.get('current_category')
        if not current_category:
            all_items = get_checklist_items(user_id, context)
            cats = list({item['category'] for item in all_items}) if all_items else []
            await safe_edit(query, "Выбери категорию:", reply_markup=categories_keyboard(cats))
            return CATEGORY_SELECT
        items = get_items_by_category(user_id, context, current_category)
        if items:
            await safe_edit(query, f"📋 {CATEGORY_NAMES.get(current_category, current_category)}:", reply_markup=checklist_keyboard(items, current_category))
        else:
            all_items = get_checklist_items(user_id, context)
            cats = list({item['category'] for item in all_items}) if all_items else []
            await safe_edit(query, "Выбери категорию:", reply_markup=categories_keyboard(cats))
            return CATEGORY_SELECT
        return CHECKLIST_VIEW

    elif data == CB_BACK_CATEGORIES:
        context.user_data.pop('current_category', None)
        all_items = get_checklist_items(user_id, context)
        cats = list({item['category'] for item in all_items}) if all_items else []
        await safe_edit(query, "📋 Выбери категорию:", reply_markup=categories_keyboard(cats))
        return CATEGORY_SELECT

    elif data == CB_BACK_MAIN:
        shift = get_active_shift(user_id)
        context.user_data.pop('current_category', None)
        await safe_edit(query, "Главное меню:", reply_markup=main_menu_keyboard(has_shift=bool(shift)))
        return MAIN_MENU

    else:
        await safe_edit(query, "Неизвестное действие", reply_markup=main_menu_keyboard(has_shift=True))
        return MAIN_MENU

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

# Заглушка для noop
async def noop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Это просто заголовок")