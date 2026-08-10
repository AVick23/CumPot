from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes, ConversationHandler
from telegram.error import BadRequest
from .constant import *
from .keyboards import *
from .utils import *
from datetime import datetime
import logging
from ..employee.constants import CATEGORY_NAMES

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

    # ============================================================
    # 1. ПРОСМОТР СМЕН
    # ============================================================
    if data == CB_ADMIN_SHIFTS:
        shifts = get_today_shifts()
        if shifts:
            text = "📋 Смены сегодня:\n"
            for s in shifts:
                text += f"• {s['first_name']} {s['last_name']} ({s['location']}) — с {s['start_time']}\n"
        else:
            text = "Сегодня никто не отметился."
        await safe_edit(query, text, reply_markup=back_to_main_button())
        return ADMIN_SHIFTS

    # ============================================================
    # 2. ПРОГРЕСС СОТРУДНИКОВ
    # ============================================================
    if data == CB_ADMIN_PROGRESS:
        employees = get_all_users()
        if not employees:
            await safe_edit(query, "Нет сотрудников.", reply_markup=back_to_main_button())
            return ADMIN_MAIN
        await safe_edit(query, "👤 Выберите сотрудника:", reply_markup=employee_list_keyboard(employees))
        return ADMIN_EMPLOYEE_LIST

    if data.startswith(CB_ADMIN_EMPLOYEE):
        employee_id = int(data.split("_")[-1])
        context.user_data['selected_employee'] = employee_id
        now = datetime.now()
        context.user_data['calendar_year'] = now.year
        context.user_data['calendar_month'] = now.month
        shift_days = get_employee_shift_days(employee_id, now.year, now.month)
        await safe_edit(query, f"📅 Выберите день (● — сотрудник был на смене):",
                        reply_markup=calendar_keyboard(now.year, now.month, shift_days))
        return ADMIN_CALENDAR

    if data == CB_ADMIN_MONTH_PREV or data == CB_ADMIN_MONTH_NEXT:
        year = context.user_data.get('calendar_year')
        month = context.user_data.get('calendar_month')
        if data == CB_ADMIN_MONTH_PREV:
            month -= 1
            if month < 1:
                month = 12
                year -= 1
        else:
            month += 1
            if month > 12:
                month = 1
                year += 1
        context.user_data['calendar_year'] = year
        context.user_data['calendar_month'] = month
        employee_id = context.user_data.get('selected_employee')
        shift_days = get_employee_shift_days(employee_id, year, month)
        await safe_edit(query, f"📅 Выберите день (● — сотрудник был на смене):",
                        reply_markup=calendar_keyboard(year, month, shift_days))
        return ADMIN_CALENDAR

    if data.startswith(CB_ADMIN_DAY):
        date_str = data.split("_")[-1]
        employee_id = context.user_data.get('selected_employee')
        items, progress = get_employee_progress(employee_id, date_str)
        if items is None:
            await safe_edit(query, "В этот день у сотрудника не было смены.", reply_markup=back_to_main_button())
            return ADMIN_MAIN
        if not items:
            await safe_edit(query, "В этот день не было задач.", reply_markup=back_to_main_button())
            return ADMIN_MAIN

        text = f"📊 Прогресс за {date_str}\n\n"
        done_total = sum(1 for item in items if item['completed'])
        total = len(items)
        text += f"Выполнено: {done_total} / {total} ({int(done_total/total*100) if total else 0}%)\n\n"

        categories_progress = {}
        for item in items:
            cat = item['category']
            if cat not in categories_progress:
                categories_progress[cat] = {'done': 0, 'total': 0, 'items': []}
            categories_progress[cat]['total'] += 1
            if item['completed']:
                categories_progress[cat]['done'] += 1
            categories_progress[cat]['items'].append(item)

        for cat, data in categories_progress.items():
            cat_name = CATEGORY_NAMES.get(cat, cat)
            text += f"\n--- {cat_name} ---\n"
            text += f"Выполнено: {data['done']} / {data['total']}\n"
            for item in data['items']:
                status = "✅" if item['completed'] else "⬜️"
                text += f"{status} {item['text']}\n"

        await safe_edit(query, text, reply_markup=progress_detail_keyboard())
        return ADMIN_DAY_PROGRESS

    if data == CB_ADMIN_BACK_TO_CALENDAR:
        employee_id = context.user_data.get('selected_employee')
        year = context.user_data.get('calendar_year')
        month = context.user_data.get('calendar_month')
        shift_days = get_employee_shift_days(employee_id, year, month)
        await safe_edit(query, f"📅 Выберите день (● — сотрудник был на смене):",
                        reply_markup=calendar_keyboard(year, month, shift_days))
        return ADMIN_CALENDAR

    # ============================================================
    # 3. РЕДАКТОР ЧЕК-ЛИСТОВ (новая логика с детальным просмотром)
    # ============================================================
    if data == CB_ADMIN_EDIT:
        all_items = get_all_checklist_items()
        if not all_items:
            await safe_edit(query, "Чек-листы пусты. Нажмите «➕ Добавить пункт», чтобы создать первый.",
                            reply_markup=edit_categories_keyboard([]))
            return ADMIN_EDIT_CATEGORIES
        categories = list({item['category'] for item in all_items})
        await safe_edit(query, "📋 Выберите категорию для редактирования:",
                        reply_markup=edit_categories_keyboard(categories))
        return ADMIN_EDIT_CATEGORIES

    if data.startswith(CB_ADMIN_EDIT_CATEGORY):
        category = data.split("_")[-1]
        context.user_data['edit_category'] = category
        items = [item for item in get_all_checklist_items() if item['category'] == category]
        await safe_edit(query, f"📋 {CATEGORY_NAMES.get(category, category)}\n"
                               f"Нажмите на пункт для просмотра и редактирования:",
                        reply_markup=edit_items_list_keyboard(items))
        return ADMIN_EDIT_ITEMS_LIST

    # === Детальный просмотр пункта ===
    if data.startswith(CB_ADMIN_VIEW_ITEM):
        item_id = int(data.split("_")[-1])
        item = next((i for i in get_all_checklist_items() if i['id'] == item_id), None)
        if not item:
            await safe_edit(query, "Пункт не найден.", reply_markup=back_to_main_button())
            return ADMIN_MAIN
        context.user_data['view_item_id'] = item_id
        text = f"📌 {item['text']}\n\n"
        text += f"Категория: {CATEGORY_NAMES.get(item['category'], item['category'])}\n"
        text += f"Локация: {'Бар' if item['location'] == 'bar' else 'Кухня'}\n"
        text += f"Тип: {'Ежедневная' if item['type'] == 'daily' else 'Недельная'}\n"
        if item['day_of_week'] is not None:
            days = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
            text += f"День недели: {days[item['day_of_week']]}\n"
        await safe_edit(query, text, reply_markup=view_item_detail_keyboard(item_id))
        return ADMIN_VIEW_ITEM

    # === Редактирование ===
    if data.startswith(CB_ADMIN_EDIT_ITEM):
        item_id = int(data.split("_")[-1])
        context.user_data['edit_item_id'] = item_id
        await safe_edit(query, "✏️ Отправьте новый текст для этого пункта:",
                        reply_markup=back_to_main_button())
        return ADMIN_AWAIT_EDIT_TEXT

    # === Удаление ===
    if data.startswith(CB_ADMIN_EDIT_DELETE):
        item_id = int(data.split("_")[-1])
        item = next((i for i in get_all_checklist_items() if i['id'] == item_id), None)
        if not item:
            await safe_edit(query, "Пункт не найден.", reply_markup=back_to_main_button())
            return ADMIN_MAIN
        await safe_edit(query, f"Удалить пункт: '{item['text'][:50]}'?\nЭто действие необратимо.",
                        reply_markup=confirm_delete_keyboard(item_id))
        return ADMIN_DELETE_CONFIRM

    if data.startswith(CB_ADMIN_EDIT_CONFIRM_DELETE):
        item_id = int(data.split("_")[-1])
        delete_checklist_item(item_id)
        all_items = get_all_checklist_items()
        if not all_items:
            await safe_edit(query, "✅ Пункт удалён. Чек-листы пусты.", reply_markup=back_to_main_button())
            return ADMIN_MAIN
        categories = list({item['category'] for item in all_items})
        await safe_edit(query, "✅ Пункт удалён. Выберите категорию:",
                        reply_markup=edit_categories_keyboard(categories))
        return ADMIN_EDIT_CATEGORIES

    if data == CB_ADMIN_EDIT_BACK:
        all_items = get_all_checklist_items()
        if not all_items:
            await safe_edit(query, "Чек-листы пусты.", reply_markup=back_to_main_button())
            return ADMIN_MAIN
        categories = list({item['category'] for item in all_items})
        await safe_edit(query, "📋 Выберите категорию для редактирования:",
                        reply_markup=edit_categories_keyboard(categories))
        return ADMIN_EDIT_CATEGORIES

    # ============================================================
    # 4. ДОБАВЛЕНИЕ НОВОГО ПУНКТА
    # ============================================================
    if data == CB_ADMIN_ADD_ITEM:
        context.user_data['new_item'] = {}
        await safe_edit(query, "Выберите тип пункта:", reply_markup=add_item_type_keyboard())
        return ADMIN_AWAIT_ITEM_TYPE

    if data.startswith(CB_ADMIN_ITEM_TYPE):
        item_type = data.split("_")[-1]
        context.user_data['new_item']['type'] = item_type
        await safe_edit(query, "Выберите локацию:", reply_markup=add_item_location_keyboard())
        return ADMIN_AWAIT_ITEM_LOCATION

    if data.startswith(CB_ADMIN_ITEM_LOCATION):
        location = data.split("_")[-1]
        context.user_data['new_item']['location'] = location
        await safe_edit(query, "Выберите категорию:", reply_markup=add_item_category_keyboard())
        return ADMIN_AWAIT_ITEM_CATEGORY

    if data.startswith(CB_ADMIN_ITEM_CATEGORY):
        category = data.split("_")[-1]
        context.user_data['new_item']['category'] = category
        if context.user_data['new_item']['type'] == 'weekly':
            await safe_edit(query, "Выберите день недели:", reply_markup=add_item_day_keyboard())
            return ADMIN_AWAIT_ITEM_DAY
        else:
            context.user_data['new_item']['day_of_week'] = None
            await safe_edit(query, "📝 Отправьте текст нового пункта одним сообщением:", reply_markup=back_to_main_button())
            return ADMIN_AWAIT_ITEM_TEXT

    if data.startswith(CB_ADMIN_ITEM_DAY):
        day = int(data.split("_")[-1])
        context.user_data['new_item']['day_of_week'] = day
        await safe_edit(query, "📝 Отправьте текст нового пункта одним сообщением:", reply_markup=back_to_main_button())
        return ADMIN_AWAIT_ITEM_TEXT

    # ============================================================
    # 5. ОБЩИЕ ДЕЙСТВИЯ
    # ============================================================
    if data == CB_ADMIN_BACK:
        await safe_edit(query, "Главное меню админа:", reply_markup=admin_main_keyboard())
        return ADMIN_MAIN

    if data == CB_ADMIN_CANCEL:
        context.user_data.pop('new_item', None)
        context.user_data.pop('edit_item_id', None)
        context.user_data.pop('view_item_id', None)
        await safe_edit(query, "Действие отменено.", reply_markup=admin_main_keyboard())
        return ADMIN_MAIN

    await safe_edit(query, "Неизвестная команда", reply_markup=admin_main_keyboard())
    return ADMIN_MAIN

async def admin_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if 'edit_item_id' in context.user_data:
        item_id = context.user_data.pop('edit_item_id')
        update_checklist_item(item_id, text)
        await update.message.reply_text("✅ Пункт обновлён!", reply_markup=admin_main_keyboard())
        return ADMIN_MAIN

    if 'new_item' in context.user_data:
        item_data = context.user_data.pop('new_item')
        add_checklist_item(
            item_data.get('type'),
            item_data.get('location'),
            item_data.get('category'),
            item_data.get('day_of_week'),
            text
        )
        await update.message.reply_text("✅ Новый пункт добавлен!", reply_markup=admin_main_keyboard())
        return ADMIN_MAIN

    await update.message.reply_text("Ошибка: неизвестное действие.", reply_markup=admin_main_keyboard())
    return ADMIN_MAIN