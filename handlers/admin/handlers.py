from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes, ConversationHandler
from telegram.error import BadRequest
from .constant import *
from .keyboards import *
from .utils import *
from db.users import get_user
import logging

logger = logging.getLogger(__name__)

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
        employees = get_all_users()
        if not employees:
            await safe_edit(query, "Нет сотрудников.", reply_markup=admin_back_keyboard())
            return ADMIN_MAIN
        await safe_edit(query, "Выбери сотрудника для просмотра прогресса:", reply_markup=employee_list_keyboard(employees))
        return ADMIN_SELECT_EMPLOYEE

    elif data == CB_ADMIN_EDIT:
        items = get_all_checklist_items()
        if not items:
            await safe_edit(query, "Чек-листы пусты. Добавьте пункты через SQL пока.", reply_markup=admin_back_keyboard())
            return ADMIN_MAIN
        await safe_edit(query, "📋 Редактор чек-листов (нажми на пункт для редактирования):", reply_markup=edit_items_keyboard(items))
        return ADMIN_EDIT_ITEMS

    elif data == CB_ADMIN_BACK:
        await safe_edit(query, "Главное меню админа:", reply_markup=admin_main_keyboard())
        return ADMIN_MAIN

    else:
        await safe_edit(query, "Неизвестная команда", reply_markup=admin_main_keyboard())
        return ADMIN_MAIN

async def employee_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith(CB_ADMIN_EMPLOYEE):
        employee_id = int(data.split("_")[-1])
        items, progress = get_employee_progress(employee_id)
        if items is None:
            await safe_edit(query, "У сотрудника нет активной смены.", reply_markup=admin_back_keyboard())
            return ADMIN_MAIN
        if not items:
            await safe_edit(query, "У сотрудника нет задач на сегодня.", reply_markup=admin_back_keyboard())
            return ADMIN_MAIN
        text = "📊 Прогресс сотрудника:\n\n"
        done = sum(1 for item in items if progress.get(item['id'], 0) == 1)
        total = len(items)
        text += f"Выполнено: {done}/{total} ({int(done/total*100) if total else 0}%)\n\n"
        for item in items:
            status = "✅" if progress.get(item['id'], 0) == 1 else "⬜"
            text += f"{status} {item['text']}\n"
        await safe_edit(query, text, reply_markup=admin_back_keyboard())
        return ADMIN_SHOW_PROGRESS
    elif data == CB_ADMIN_BACK:
        await safe_edit(query, "Главное меню админа:", reply_markup=admin_main_keyboard())
        return ADMIN_MAIN
    else:
        await safe_edit(query, "Неизвестный выбор", reply_markup=admin_main_keyboard())
        return ADMIN_MAIN

async def edit_items_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == CB_ADMIN_EDIT_ITEMS:
        items = get_all_checklist_items()
        if not items:
            await safe_edit(query, "Чек-листы пусты.", reply_markup=admin_back_keyboard())
            return ADMIN_MAIN
        await safe_edit(query, "📋 Редактор чек-листов:", reply_markup=edit_items_keyboard(items))
        return ADMIN_EDIT_ITEMS

    elif data.startswith(CB_ADMIN_EDIT_ITEM):
        item_id = int(data.split("_")[-1])
        item = next((i for i in get_all_checklist_items() if i['id'] == item_id), None)
        if not item:
            await safe_edit(query, "Пункт не найден.", reply_markup=admin_back_keyboard())
            return ADMIN_MAIN
        text = f"✏️ Редактирование пункта:\n\n"
        text += f"ID: {item['id']}\n"
        text += f"Локация: {item['location']}\n"
        text += f"Категория: {item['category']}\n"
        text += f"Тип: {item['type']}\n"
        if item['day_of_week'] is not None:
            text += f"День недели: {item['day_of_week']}\n"
        text += f"Текст: {item['text']}\n"
        await safe_edit(query, text, reply_markup=edit_item_detail_keyboard(item_id))
        return ADMIN_EDIT_ITEM

    elif data.startswith(CB_ADMIN_DELETE_ITEM):
        item_id = int(data.split("_")[-1])
        await safe_edit(query, "Удалить этот пункт?", reply_markup=confirm_delete_keyboard(item_id))
        return ADMIN_DELETE_ITEM

    elif data.startswith(CB_ADMIN_CONFIRM_DELETE):
        item_id = int(data.split("_")[-1])
        delete_checklist_item(item_id)
        items = get_all_checklist_items()
        if not items:
            await safe_edit(query, "✅ Пункт удалён. Чек-листы пусты.", reply_markup=admin_back_keyboard())
            return ADMIN_MAIN
        await safe_edit(query, "✅ Пункт удалён. Список обновлён:", reply_markup=edit_items_keyboard(items))
        return ADMIN_EDIT_ITEMS

    elif data == CB_ADMIN_ADD_ITEM:
        await safe_edit(query, "Функция добавления через бота пока в разработке.\n\n"
                              "Пожалуйста, используйте прямой SQL-запрос для добавления.\n"
                              "Пример:\n"
                              "INSERT INTO checklist_items (type, location, category, day_of_week, sort_order, text)\n"
                              "VALUES ('daily', 'bar', 'opening', NULL, 1, 'Включить свет');",
                              reply_markup=admin_back_keyboard())
        return ADMIN_MAIN

    elif data == CB_ADMIN_BACK:
        await safe_edit(query, "Главное меню админа:", reply_markup=admin_main_keyboard())
        return ADMIN_MAIN

    else:
        await safe_edit(query, "Неизвестное действие", reply_markup=admin_main_keyboard())
        return ADMIN_MAIN