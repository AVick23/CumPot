from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes, ConversationHandler
from telegram.error import BadRequest
from .constant import *
from .keyboards import *
from .utils import *
from datetime import datetime
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
    user_id = query.from_user.id

    # Обработка выбора сотрудника для просмотра прогресса
    if data == CB_ADMIN_PROGRESS:
        employees = get_all_users()
        if not employees:
            await safe_edit(query, "Нет сотрудников.", reply_markup=admin_back_keyboard())
            return ADMIN_MAIN
        await safe_edit(query, "Выбери сотрудника для просмотра прогресса:", reply_markup=employee_list_keyboard(employees))
        return ADMIN_SELECT_EMPLOYEE

    elif data.startswith(CB_ADMIN_EMPLOYEE):
        employee_id = int(data.split("_")[-1])
        context.user_data['selected_employee'] = employee_id
        now = datetime.now()
        context.user_data['calendar_year'] = now.year
        context.user_data['calendar_month'] = now.month
        # Получаем дни смен
        shift_days = get_employee_shift_days(employee_id, now.year, now.month)
        await safe_edit(query, f"📅 Выбери день в календаре (✅ — были на смене):",
                        reply_markup=calendar_keyboard(now.year, now.month, shift_days))
        return ADMIN_CALENDAR

    # Навигация по календарю
    elif data == CB_ADMIN_MONTH_PREV:
        year = context.user_data.get('calendar_year')
        month = context.user_data.get('calendar_month')
        if month == 1:
            month = 12
            year -= 1
        else:
            month -= 1
        context.user_data['calendar_year'] = year
        context.user_data['calendar_month'] = month
        employee_id = context.user_data.get('selected_employee')
        shift_days = get_employee_shift_days(employee_id, year, month)
        await safe_edit(query, f"📅 Выбери день в календаре (✅ — были на смене):",
                        reply_markup=calendar_keyboard(year, month, shift_days))
        return ADMIN_CALENDAR

    elif data == CB_ADMIN_MONTH_NEXT:
        year = context.user_data.get('calendar_year')
        month = context.user_data.get('calendar_month')
        if month == 12:
            month = 1
            year += 1
        else:
            month += 1
        context.user_data['calendar_year'] = year
        context.user_data['calendar_month'] = month
        employee_id = context.user_data.get('selected_employee')
        shift_days = get_employee_shift_days(employee_id, year, month)
        await safe_edit(query, f"📅 Выбери день в календаре (✅ — были на смене):",
                        reply_markup=calendar_keyboard(year, month, shift_days))
        return ADMIN_CALENDAR

    # Выбор конкретного дня
    elif data.startswith(CB_ADMIN_DAY):
        date_str = data.split("_")[-1]
        employee_id = context.user_data.get('selected_employee')
        items, progress = get_employee_progress(employee_id, date_str)
        if items is None:
            await safe_edit(query, "В этот день у сотрудника не было смены или нет данных.", reply_markup=admin_back_keyboard())
            return ADMIN_MAIN
        if not items:
            await safe_edit(query, "В этот день у сотрудника не было задач.", reply_markup=admin_back_keyboard())
            return ADMIN_MAIN
        # Формируем отчёт
        text = f"📊 Прогресс сотрудника за {date_str}:\n\n"
        done = sum(1 for item in items if item['completed'])
        total = len(items)
        text += f"Выполнено: {done}/{total} ({int(done/total*100) if total else 0}%)\n\n"
        for item in items:
            status = "✅" if item['completed'] else "⬜"
            text += f"{status} {item['text']}\n"
        await safe_edit(query, text, reply_markup=progress_detail_keyboard(employee_id, date_str))
        return ADMIN_DAY_PROGRESS

    # Возврат к календарю из деталей прогресса
    elif data == CB_ADMIN_BACK_TO_CALENDAR:
        employee_id = context.user_data.get('selected_employee')
        year = context.user_data.get('calendar_year')
        month = context.user_data.get('calendar_month')
        shift_days = get_employee_shift_days(employee_id, year, month)
        await safe_edit(query, f"📅 Выбери день в календаре (✅ — были на смене):",
                        reply_markup=calendar_keyboard(year, month, shift_days))
        return ADMIN_CALENDAR

    # Остальные функции (редактор, смены сегодня и т.д.) без изменений
    elif data == CB_ADMIN_SHIFTS:
        shifts = get_today_shifts()
        if shifts:
            text = "📋 Смены сегодня:\n"
            for s in shifts:
                text += f"- {s['first_name']} {s['last_name']} ({s['location']}) с {s['start_time']}\n"
        else:
            text = "Сегодня никто не отметился."
        await safe_edit(query, text, reply_markup=admin_back_keyboard())
        return ADMIN_SHIFTS

    elif data == CB_ADMIN_EDIT:
        items = get_all_checklist_items()
        if not items:
            await safe_edit(query, "Чек-листы пусты. Нажми «➕ Добавить пункт», чтобы создать первый.", reply_markup=edit_items_keyboard(items))
            return ADMIN_EDIT_ITEMS
        await safe_edit(query, "📋 Редактор чек-листов (нажми на пункт для редактирования):", reply_markup=edit_items_keyboard(items))
        return ADMIN_EDIT_ITEMS

    # Редактирование пунктов (без изменений)
    elif data.startswith(CB_ADMIN_EDIT_ITEM):
        item_id = int(data.split("_")[-1])
        context.user_data['edit_item_id'] = item_id
        await safe_edit(query, "Отправь новый текст для этого пункта одним сообщением:", reply_markup=admin_back_keyboard())
        return ADMIN_AWAIT_EDIT_TEXT

    elif data.startswith(CB_ADMIN_DELETE_ITEM):
        item_id = int(data.split("_")[-1])
        item = next((i for i in get_all_checklist_items() if i['id'] == item_id), None)
        if not item:
            await safe_edit(query, "Пункт не найден.", reply_markup=admin_back_keyboard())
            return ADMIN_MAIN
        await safe_edit(query, f"Удалить пункт: '{item['text'][:50]}'?\nЭто действие необратимо.", reply_markup=confirm_delete_keyboard(item_id))
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
        context.user_data['new_item'] = {}
        await safe_edit(query, "Выбери тип пункта:", reply_markup=add_item_type_keyboard())
        return ADMIN_AWAIT_ITEM_TYPE

    elif data.startswith(CB_ADMIN_ITEM_TYPE):
        item_type = data.split("_")[-1]
        context.user_data['new_item']['type'] = item_type
        await safe_edit(query, "Выбери локацию:", reply_markup=add_item_location_keyboard())
        return ADMIN_AWAIT_ITEM_LOCATION

    elif data.startswith(CB_ADMIN_ITEM_LOCATION):
        location = data.split("_")[-1]
        context.user_data['new_item']['location'] = location
        await safe_edit(query, "Выбери категорию:", reply_markup=add_item_category_keyboard())
        return ADMIN_AWAIT_ITEM_CATEGORY

    elif data.startswith(CB_ADMIN_ITEM_CATEGORY):
        category = data.split("_")[-1]
        context.user_data['new_item']['category'] = category
        if context.user_data['new_item']['type'] == 'weekly':
            await safe_edit(query, "Выбери день недели:", reply_markup=add_item_day_keyboard())
            return ADMIN_AWAIT_ITEM_DAY
        else:
            context.user_data['new_item']['day_of_week'] = None
            await safe_edit(query, "Отправь текст нового пункта одним сообщением:", reply_markup=admin_back_keyboard())
            return ADMIN_AWAIT_ITEM_TEXT

    elif data.startswith(CB_ADMIN_ITEM_DAY):
        day = int(data.split("_")[-1])
        context.user_data['new_item']['day_of_week'] = day
        await safe_edit(query, "Отправь текст нового пункта одним сообщением:", reply_markup=admin_back_keyboard())
        return ADMIN_AWAIT_ITEM_TEXT

    elif data == CB_ADMIN_EDIT_ITEMS:
        items = get_all_checklist_items()
        if not items:
            await safe_edit(query, "Чек-листы пусты.", reply_markup=admin_back_keyboard())
            return ADMIN_MAIN
        await safe_edit(query, "📋 Редактор чек-листов:", reply_markup=edit_items_keyboard(items))
        return ADMIN_EDIT_ITEMS

    elif data == CB_ADMIN_CANCEL:
        context.user_data.pop('new_item', None)
        context.user_data.pop('edit_item_id', None)
        await safe_edit(query, "Действие отменено.", reply_markup=admin_main_keyboard())
        return ADMIN_MAIN

    elif data == CB_ADMIN_BACK:
        # Возврат в главное меню из любого места
        await safe_edit(query, "Главное меню админа:", reply_markup=admin_main_keyboard())
        return ADMIN_MAIN

    else:
        await safe_edit(query, "Неизвестная команда", reply_markup=admin_main_keyboard())
        return ADMIN_MAIN

async def admin_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстового ввода (новый пункт или редактирование)"""
    text = update.message.text
    user_id = update.effective_user.id

    # Редактирование существующего пункта
    if 'edit_item_id' in context.user_data:
        item_id = context.user_data.pop('edit_item_id')
        update_checklist_item(item_id, text)
        await update.message.reply_text("✅ Пункт обновлён!", reply_markup=admin_main_keyboard())
        context.user_data.pop('edit_item_id', None)
        return ADMIN_MAIN

    # Добавление нового пункта
    if 'new_item' in context.user_data:
        item_data = context.user_data.pop('new_item')
        item_type = item_data.get('type')
        location = item_data.get('location')
        category = item_data.get('category')
        day_of_week = item_data.get('day_of_week')
        add_checklist_item(item_type, location, category, day_of_week, text)
        await update.message.reply_text("✅ Новый пункт добавлен!", reply_markup=admin_main_keyboard())
        return ADMIN_MAIN

    await update.message.reply_text("Ошибка: неизвестное действие.", reply_markup=admin_main_keyboard())
    return ADMIN_MAIN