from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from .constants import (
    ADMIN_EDIT_LOCATION, ADMIN_EDIT_CATEGORY, ADMIN_EDIT_ITEMS,
    ADMIN_ITEM_DETAIL, ADMIN_DELETE_CONFIRM, ADMIN_ADD_DAY,
    ADMIN_AWAIT_NEW_TEXT, ADMIN_AWAIT_EDIT_TEXT,
    ADMIN_AWAIT_ITEM_TYPE, ADMIN_AWAIT_DATE,
    ADMIN_AWAIT_HOUR, ADMIN_AWAIT_MINUTE,
    ADMIN_AWAIT_PHOTO_FLAG, ADMIN_AWAIT_NOTIFICATION_FLAG,
    ADMIN_AWAIT_DAYS,
    ADMIN_EDIT_TOGGLE_PHOTO, ADMIN_EDIT_TOGGLE_NOTIFICATION, ADMIN_EDIT_CHANGE_TIME,
    CB_HOME, CB_TO_EDIT, CB_TO_CATEGORIES, CB_TO_ITEMS,
    CB_LOC_PREFIX, CB_CAT_PREFIX, CB_PAGE_PREFIX,
    CB_ITEM_PREFIX, CB_EDIT_ITEM_PREFIX, CB_DELETE_ITEM_PREFIX,
    CB_CONFIRM_DELETE_PREFIX, CB_ADD, CB_ADD_DAY_PREFIX,
    CB_ADD_BACK_TEXT, CB_CANCEL, CB_CANCEL_EDIT,
    CB_ITEM_TYPE_PREFIX, CB_DATE_PREFIX, CB_MONTH_PREV, CB_MONTH_NEXT,
    CB_HOUR_PREFIX, CB_MINUTE_PREFIX,
    CB_PHOTO_FLAG_PREFIX, CB_NOTIF_FLAG_PREFIX, CB_FLAGS_SKIP,
    CB_TOGGLE_PHOTO, CB_TOGGLE_NOTIFICATION, CB_CHANGE_TIME,
    CB_BACK_FROM_EDIT,
    CB_DAY_TOGGLE_PREFIX, CB_DAYS_CONFIRM, CB_DAYS_CANCEL,
    LOCATIONS, CATEGORY_LABELS, WEEKDAYS_SHORT,
    TEXT_LIMIT,
)
from .keyboards import (
    edit_location_keyboard, edit_category_keyboard, items_list_keyboard,
    item_detail_keyboard, confirm_delete_keyboard, add_day_keyboard,
    text_prompt_keyboard, item_type_keyboard,
    calendar_keyboard, hour_keyboard, minute_keyboard,
    flag_photo_keyboard, flag_notification_keyboard, flags_skip_keyboard,
    days_selection_keyboard,
)
from .utils import (
    get_location_counts, get_category_counts, get_items_for_editor,
    paginate_items, get_item, create_item, update_item_text,
    update_item_flags, update_item_days, remove_item, render, parse_due_date,
    get_breadcrumb,
)
import logging

logger = logging.getLogger(__name__)

# ==================== НАВИГАЦИЯ ====================
async def show_edit_locations(update: Update, context: ContextTypes.DEFAULT_TYPE,
                              message_id=None, notice=None) -> int:
    context.user_data.pop("edit_location", None)
    context.user_data.pop("edit_category", None)
    context.user_data.pop("edit_page", None)
    counts = get_location_counts()
    breadcrumb = get_breadcrumb()
    text = f"{breadcrumb}\n\n📝 Чек-листы\n\nВыберите локацию."
    if notice:
        text = f"{notice}\n\n{text}"
    await render(update, context, text, edit_location_keyboard(counts), message_id)
    return ADMIN_EDIT_LOCATION


async def show_edit_categories(update: Update, context: ContextTypes.DEFAULT_TYPE,
                               message_id=None, location=None, notice=None) -> int:
    location = location or context.user_data.get("edit_location")
    if location not in LOCATIONS:
        return await show_edit_locations(update, context, message_id, "⚠️ Выберите локацию.")
    context.user_data["edit_location"] = location
    context.user_data.pop("edit_category", None)
    context.user_data.pop("edit_page", None)
    counts = get_category_counts(location)
    breadcrumb = get_breadcrumb(location)
    text = f"{breadcrumb}\n\nВыберите категорию."
    if notice:
        text = f"{notice}\n\n{text}"
    await render(update, context, text, edit_category_keyboard(location, counts), message_id)
    return ADMIN_EDIT_CATEGORY


async def show_items_list(update: Update, context: ContextTypes.DEFAULT_TYPE,
                          message_id=None, location=None, category=None,
                          page=None, notice=None) -> int:
    location = location or context.user_data.get("edit_location")
    category = category or context.user_data.get("edit_category")
    if location not in LOCATIONS:
        return await show_edit_locations(update, context, message_id, "⚠️ Выберите локацию.")
    if category not in CATEGORY_LABELS:
        return await show_edit_categories(update, context, message_id, location, "⚠️ Выберите категорию.")
    page = page or context.user_data.get("edit_page", 1)
    items = get_items_for_editor(location, category)
    page_items, total_pages, page = paginate_items(items, page)
    context.user_data["edit_location"] = location
    context.user_data["edit_category"] = category
    context.user_data["edit_page"] = page
    breadcrumb = get_breadcrumb(location, category)
    header = f"{breadcrumb}\n\nПунктов: {len(items)}"
    if total_pages > 1:
        header += f" · стр. {page}/{total_pages}"
    header += "\n\nНажмите на пункт, чтобы посмотреть или изменить." if page_items else "\n\nПока пусто. Добавьте первый пункт."
    if notice:
        header = f"{notice}\n\n{header}"
    await render(update, context, header, items_list_keyboard(location, category, page_items, page, total_pages), message_id)
    return ADMIN_EDIT_ITEMS


async def show_item_detail(update: Update, context: ContextTypes.DEFAULT_TYPE,
                           item_id, message_id=None, notice=None) -> int:
    item = get_item(item_id)
    if not item:
        return await show_items_list(update, context, message_id, notice="⚠️ Пункт не найден.")
    context.user_data["edit_location"] = item["location"]
    context.user_data["edit_category"] = item["category"]
    context.user_data["last_item_id"] = item_id
    breadcrumb = get_breadcrumb(item["location"], item["category"])
    loc_label = LOCATIONS.get(item["location"], item["location"])
    cat_label = CATEGORY_LABELS.get(item["category"], item["category"])
    type_label = "ежедневный" if item["type"] == "daily" else "недельный" if item["type"] == "weekly" else "одноразовый"
    lines = [f"{breadcrumb}\n\n📝 Пункт чек-листа", "", item.get("text") or "", "",
             f"Локация: {loc_label}", f"Категория: {cat_label}", f"Тип: {type_label}"]
    if item["type"] == "weekly" and item.get("days_of_week"):
        day_list = [WEEKDAYS_SHORT[int(d)] for d in item["days_of_week"].split(",") if d.isdigit()]
        lines.append(f"Дни: {', '.join(day_list)}")
    elif item["type"] == "weekly" and item.get("day_of_week") is not None:
        lines.append(f"День: {WEEKDAYS_SHORT[item['day_of_week']]}")
    if item["type"] == "once" and item.get("due_date"):
        lines.append(f"Дата: {item['due_date']}")
    lines.append(f"Требуется фото: {'✅' if item.get('requires_photo') else '❌'}")
    lines.append(f"Требуется уведомление: {'✅' if item.get('requires_notification') else '❌'}")
    if item.get("requires_notification") and item.get("notification_time"):
        lines.append(f"Время уведомления: {item['notification_time']}")
    text = "\n".join(lines)
    if notice:
        text = f"{notice}\n\n{text}"
    await render(update, context, text, item_detail_keyboard(item), message_id)
    return ADMIN_ITEM_DETAIL


# ==================== ДОБАВЛЕНИЕ ====================
async def start_add(update: Update, context: ContextTypes.DEFAULT_TYPE,
                    message_id=None) -> int:
    location = context.user_data.get("edit_location")
    category = context.user_data.get("edit_category")
    if location not in LOCATIONS or category not in CATEGORY_LABELS:
        return await show_edit_locations(update, context, message_id, "⚠️ Сначала выберите категорию.")
    # Очищаем данные
    for key in ["add_item_type", "add_days", "add_due_date", "add_hour", "add_minute",
                "add_requires_photo", "add_requires_notification", "add_flow", "add_final", "add_text"]:
        context.user_data.pop(key, None)
    context.user_data["add_flow"] = {"location": location, "category": category}
    breadcrumb = get_breadcrumb(location, category)
    text = f"{breadcrumb}\n\nВыберите тип задачи:"
    await render(update, context, text, item_type_keyboard(), message_id)
    return ADMIN_AWAIT_ITEM_TYPE


async def item_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None
    flow = context.user_data.get("add_flow") or {}
    location, category = flow.get("location"), flow.get("category")

    if data.startswith(CB_ITEM_TYPE_PREFIX):
        item_type = data.split(":", 1)[1]
        context.user_data["add_item_type"] = item_type

        if item_type == "weekly":
            # Показываем выбор дней
            context.user_data["selected_days"] = set()
            breadcrumb = get_breadcrumb(location, category)
            text = f"{breadcrumb}\n\nВыберите дни недели (можно несколько):"
            await render(update, context, text, days_selection_keyboard(set()), message_id)
            return ADMIN_AWAIT_DAYS
        elif item_type == "once":
            now = datetime.now()
            year = context.user_data.get("calendar_year", now.year)
            month = context.user_data.get("calendar_month", now.month)
            context.user_data["calendar_year"] = year
            context.user_data["calendar_month"] = month
            breadcrumb = get_breadcrumb(location, category)
            text = f"{breadcrumb}\n\nВыберите дату:"
            await render(update, context, text, calendar_keyboard(year, month), message_id)
            return ADMIN_AWAIT_DATE
        else:  # daily
            # Переходим к вводу текста
            return await ask_text(update, context, message_id)

    if data == CB_CANCEL:
        return await cancel_action(update, context, message_id)

    return await show_edit_locations(update, context, message_id)


async def days_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None
    flow = context.user_data.get("add_flow") or {}
    location, category = flow.get("location"), flow.get("category")
    selected = context.user_data.get("selected_days", set())

    if data.startswith(CB_DAY_TOGGLE_PREFIX):
        day = int(data.split(":")[1])
        if day in selected:
            selected.remove(day)
        else:
            selected.add(day)
        context.user_data["selected_days"] = selected
        breadcrumb = get_breadcrumb(location, category)
        text = f"{breadcrumb}\n\nВыберите дни недели (можно несколько):"
        await render(update, context, text, days_selection_keyboard(selected), message_id)
        return ADMIN_AWAIT_DAYS

    elif data == CB_DAYS_CONFIRM:
        if not selected:
            await query.answer("Выберите хотя бы один день")
            return ADMIN_AWAIT_DAYS
        days_str = ",".join(str(d) for d in sorted(selected))
        context.user_data["add_days"] = days_str
        # Переходим к вводу текста
        return await ask_text(update, context, message_id)

    elif data == CB_DAYS_CANCEL:
        context.user_data.pop("selected_days", None)
        return await cancel_action(update, context, message_id)

    return await show_edit_locations(update, context, message_id)


async def date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None
    flow = context.user_data.get("add_flow") or {}
    location, category = flow.get("location"), flow.get("category")

    if data == CB_MONTH_PREV:
        year = context.user_data.get("calendar_year")
        month = context.user_data.get("calendar_month")
        if month == 1:
            month = 12
            year -= 1
        else:
            month -= 1
        context.user_data["calendar_year"] = year
        context.user_data["calendar_month"] = month
        breadcrumb = get_breadcrumb(location, category)
        text = f"{breadcrumb}\n\nВыберите дату:"
        await render(update, context, text, calendar_keyboard(year, month), message_id)
        return ADMIN_AWAIT_DATE

    if data == CB_MONTH_NEXT:
        year = context.user_data.get("calendar_year")
        month = context.user_data.get("calendar_month")
        if month == 12:
            month = 1
            year += 1
        else:
            month += 1
        context.user_data["calendar_year"] = year
        context.user_data["calendar_month"] = month
        breadcrumb = get_breadcrumb(location, category)
        text = f"{breadcrumb}\n\nВыберите дату:"
        await render(update, context, text, calendar_keyboard(year, month), message_id)
        return ADMIN_AWAIT_DATE

    if data.startswith(CB_DATE_PREFIX):
        due_date = data.split(":", 1)[1]  # YYYY-MM-DD
        context.user_data["add_due_date"] = due_date
        # Переходим к вводу текста
        return await ask_text(update, context, message_id)

    if data == CB_CANCEL:
        return await cancel_action(update, context, message_id)

    return await show_edit_locations(update, context, message_id)


async def ask_text(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id=None) -> int:
    flow = context.user_data.get("add_flow") or {}
    location, category = flow.get("location"), flow.get("category")
    breadcrumb = get_breadcrumb(location, category)
    text = f"{breadcrumb}\n\nОтправьте текст задачи обычным сообщением."
    kb = text_prompt_keyboard(CB_CANCEL)
    new_mid = await render(update, context, text, kb, message_id)
    context.user_data["await_text"] = {
        "kind": "new",
        "state": ADMIN_AWAIT_NEW_TEXT,
        "message_id": new_mid
    }
    return ADMIN_AWAIT_NEW_TEXT


async def ask_photo_flag(update: Update, context: ContextTypes.DEFAULT_TYPE,
                         message_id=None) -> int:
    flow = context.user_data.get("add_flow") or {}
    location, category = flow.get("location"), flow.get("category")
    breadcrumb = get_breadcrumb(location, category)
    text = f"{breadcrumb}\n\nТребуется ли фото для этой задачи?"
    await render(update, context, text, flag_photo_keyboard(), message_id)
    return ADMIN_AWAIT_PHOTO_FLAG


async def photo_flag_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None

    if data.startswith(CB_PHOTO_FLAG_PREFIX):
        value = data.split(":", 1)[1]
        context.user_data["add_requires_photo"] = (value == "yes")
        return await ask_notification_flag(update, context, message_id)

    if data == CB_CANCEL:
        return await cancel_action(update, context, message_id)

    return await show_edit_locations(update, context, message_id)


async def ask_notification_flag(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                message_id=None) -> int:
    flow = context.user_data.get("add_flow") or {}
    location, category = flow.get("location"), flow.get("category")
    breadcrumb = get_breadcrumb(location, category)
    text = f"{breadcrumb}\n\nТребуется ли уведомление для этой задачи?\n(Уведомление будет отправлено всем, кто на смене в день выполнения)"
    await render(update, context, text, flag_notification_keyboard(), message_id)
    return ADMIN_AWAIT_NOTIFICATION_FLAG


async def notification_flag_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None

    if data.startswith(CB_NOTIF_FLAG_PREFIX):
        value = data.split(":", 1)[1]
        context.user_data["add_requires_notification"] = (value == "yes")
        # Если уведомление включено, запрашиваем время
        if context.user_data.get("add_requires_notification"):
            return await ask_hour(update, context, message_id)
        else:
            return await finish_add(update, context, message_id)

    if data == CB_CANCEL:
        return await cancel_action(update, context, message_id)

    return await show_edit_locations(update, context, message_id)


async def ask_hour(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id=None) -> int:
    flow = context.user_data.get("add_flow") or {}
    location, category = flow.get("location"), flow.get("category")
    breadcrumb = get_breadcrumb(location, category)
    text = f"{breadcrumb}\n\nВыберите час:"
    await render(update, context, text, hour_keyboard(), message_id)
    return ADMIN_AWAIT_HOUR


async def hour_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None

    if data.startswith(CB_HOUR_PREFIX):
        hour = int(data.split(":", 1)[1])
        context.user_data["add_hour"] = hour
        return await ask_minute(update, context, message_id)

    if data == CB_CANCEL:
        return await cancel_action(update, context, message_id)

    return await show_edit_locations(update, context, message_id)


async def ask_minute(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id=None) -> int:
    flow = context.user_data.get("add_flow") or {}
    location, category = flow.get("location"), flow.get("category")
    breadcrumb = get_breadcrumb(location, category)
    text = f"{breadcrumb}\n\nВыберите минуты (с шагом 5):"
    await render(update, context, text, minute_keyboard(), message_id)
    return ADMIN_AWAIT_MINUTE


async def minute_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None

    if data.startswith(CB_MINUTE_PREFIX):
        minute = int(data.split(":", 1)[1])
        context.user_data["add_minute"] = minute
        return await finish_add(update, context, message_id)

    if data == CB_CANCEL:
        return await cancel_action(update, context, message_id)

    return await show_edit_locations(update, context, message_id)


async def finish_add(update: Update, context: ContextTypes.DEFAULT_TYPE,
                     message_id=None) -> int:
    flow = context.user_data.get("add_flow") or {}
    location = flow.get("location")
    category = flow.get("category")
    item_type = context.user_data.get("add_item_type")
    days_str = context.user_data.get("add_days")  # для weekly
    due_date = context.user_data.get("add_due_date")  # для once
    hour = context.user_data.get("add_hour")
    minute = context.user_data.get("add_minute")
    requires_photo = context.user_data.get("add_requires_photo", False)
    requires_notification = context.user_data.get("add_requires_notification", False)
    text = context.user_data.get("add_text")

    if not text:
        return await ask_text(update, context, message_id)

    is_recurring = (item_type != "once")
    day_of_week = None
    if item_type == "weekly" and days_str:
        # для совместимости сохраняем первый день в day_of_week
        first_day = int(days_str.split(",")[0]) if days_str else None
        day_of_week = first_day
    elif item_type == "once":
        day_of_week = None

    notification_time = None
    if requires_notification and hour is not None and minute is not None:
        notification_time = f"{hour:02d}:{minute:02d}"
    elif requires_notification:
        return await ask_hour(update, context, message_id)

    create_item(
        item_type=item_type,
        location=location,
        category=category,
        day_of_week=day_of_week,
        days_of_week=days_str,
        text=text,
        requires_photo=requires_photo,
        requires_notification=requires_notification,
        notification_time=notification_time,
        due_date=due_date,
        is_recurring=is_recurring
    )

    # Очищаем данные
    for key in ["add_flow", "add_item_type", "add_days", "add_due_date", "add_hour", "add_minute",
                "add_requires_photo", "add_requires_notification", "add_text", "await_text", "selected_days"]:
        context.user_data.pop(key, None)

    return await show_items_list(update, context, message_id, location=location,
                                 category=category, page=999999, notice="✅ Пункт добавлен.")


# ==================== РЕДАКТИРОВАНИЕ ====================
async def prompt_edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE,
                           item_id, message_id=None) -> int:
    item = get_item(item_id)
    if not item:
        return await show_items_list(update, context, message_id, notice="⚠️ Пункт не найден.")
    context.user_data["last_item_id"] = item_id
    breadcrumb = get_breadcrumb(item["location"], item["category"])
    text = f"{breadcrumb}\n\n✏️ Редактирование\n\nТекущий текст:\n{item.get('text')}\n\nОтправьте новый текст обычным сообщением."
    kb = text_prompt_keyboard(CB_CANCEL_EDIT)
    new_mid = await render(update, context, text, kb, message_id)
    context.user_data["await_text"] = {"kind": "edit", "item_id": item_id,
                                       "state": ADMIN_AWAIT_EDIT_TEXT, "message_id": new_mid}
    return ADMIN_AWAIT_EDIT_TEXT


async def cancel_edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE,
                           message_id=None) -> int:
    meta = context.user_data.get("await_text") or {}
    item_id = meta.get("item_id") or context.user_data.get("last_item_id")
    context.user_data.pop("await_text", None)
    if item_id:
        return await show_item_detail(update, context, item_id, message_id, notice="Отменено.")
    return await show_items_list(update, context, message_id, notice="Отменено.")


async def edit_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    meta = context.user_data.get("await_text")
    if not meta:
        return await show_edit_locations(update, context, None, notice="Начните заново с /start.")
    text = (update.message.text or "").strip() if update.message else ""
    message_id = meta.get("message_id")

    if not text:
        kb = text_prompt_keyboard(CB_CANCEL)
        await render(update, context, "⚠️ Текст не может быть пустым. Попробуйте ещё раз.", kb, message_id)
        return meta.get("state", ADMIN_EDIT_LOCATION)

    if len(text) > TEXT_LIMIT:
        kb = text_prompt_keyboard(CB_CANCEL)
        await render(update, context, f"⚠️ Слишком длинно. Максимум {TEXT_LIMIT} символов.\n\nОтправьте текст ещё раз.", kb, message_id)
        return meta.get("state", ADMIN_EDIT_LOCATION)

    if meta.get("kind") == "new":
        context.user_data["add_text"] = text
        return await ask_photo_flag(update, context, message_id)

    elif meta.get("kind") == "edit":
        item_id = meta.get("item_id")
        if not item_id:
            return await show_items_list(update, context, message_id)
        update_item_text(item_id, text)
        context.user_data.pop("await_text", None)
        return await show_item_detail(update, context, item_id, message_id, notice="✅ Сохранено.")

    return await show_edit_locations(update, context, message_id)


# ==================== ДЕЙСТВИЯ С ЗАДАЧАМИ ====================
async def toggle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: int, message_id: int) -> int:
    item = get_item(item_id)
    if not item:
        return await show_items_list(update, context, message_id, notice="⚠️ Пункт не найден.")
    new_value = not item.get("requires_photo")
    update_item_flags(item_id, requires_photo=new_value)
    return await show_item_detail(update, context, item_id, message_id, notice=f"✅ Фото: {'включено' if new_value else 'выключено'}")


async def toggle_notification(update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: int, message_id: int) -> int:
    item = get_item(item_id)
    if not item:
        return await show_items_list(update, context, message_id, notice="⚠️ Пункт не найден.")
    new_value = not item.get("requires_notification")
    if new_value and not item.get("notification_time"):
        context.user_data["edit_item_id"] = item_id
        context.user_data["edit_new_notification"] = True
        breadcrumb = get_breadcrumb(item["location"], item["category"])
        text = f"{breadcrumb}\n\nВведите время уведомления (часы и минуты):"
        await render(update, context, text, hour_keyboard(), message_id)
        return ADMIN_AWAIT_HOUR
    else:
        update_item_flags(item_id, requires_notification=new_value)
        return await show_item_detail(update, context, item_id, message_id, notice=f"✅ Уведомление: {'включено' if new_value else 'выключено'}")


async def change_time(update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: int, message_id: int) -> int:
    item = get_item(item_id)
    if not item:
        return await show_items_list(update, context, message_id, notice="⚠️ Пункт не найден.")
    context.user_data["edit_item_id"] = item_id
    context.user_data["edit_new_notification"] = False
    breadcrumb = get_breadcrumb(item["location"], item["category"])
    text = f"{breadcrumb}\n\nВыберите новое время уведомления:"
    await render(update, context, text, hour_keyboard(), message_id)
    return ADMIN_AWAIT_HOUR


async def handle_hour_selection_for_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None
    item_id = context.user_data.get("edit_item_id")
    if not item_id:
        return await show_items_list(update, context, message_id, notice="⚠️ Ошибка: не найден ID задачи.")

    if data.startswith(CB_HOUR_PREFIX):
        hour = int(data.split(":", 1)[1])
        context.user_data["edit_hour"] = hour
        await render(update, context, "Выберите минуты (с шагом 5):", minute_keyboard(), message_id)
        return ADMIN_AWAIT_MINUTE

    if data == CB_CANCEL:
        context.user_data.pop("edit_item_id", None)
        context.user_data.pop("edit_hour", None)
        return await show_item_detail(update, context, item_id, message_id, notice="Отменено.")

    return await show_edit_locations(update, context, message_id)


async def handle_minute_selection_for_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None
    item_id = context.user_data.get("edit_item_id")
    if not item_id:
        return await show_items_list(update, context, message_id, notice="⚠️ Ошибка: не найден ID задачи.")

    if data.startswith(CB_MINUTE_PREFIX):
        minute = int(data.split(":", 1)[1])
        hour = context.user_data.get("edit_hour")
        if hour is None:
            return await show_item_detail(update, context, item_id, message_id, notice="⚠️ Ошибка: час не выбран.")
        notification_time = f"{hour:02d}:{minute:02d}"
        update_item_flags(item_id, requires_notification=True, notification_time=notification_time)
        context.user_data.pop("edit_item_id", None)
        context.user_data.pop("edit_hour", None)
        return await show_item_detail(update, context, item_id, message_id, notice=f"✅ Время уведомления обновлено: {notification_time}")

    if data == CB_CANCEL:
        context.user_data.pop("edit_item_id", None)
        context.user_data.pop("edit_hour", None)
        return await show_item_detail(update, context, item_id, message_id, notice="Отменено.")

    return await show_edit_locations(update, context, message_id)


async def edit_days(update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: int, message_id: int) -> int:
    """Редактирование дней для weekly задачи."""
    item = get_item(item_id)
    if not item or item.get("type") != "weekly":
        return await show_items_list(update, context, message_id, notice="⚠️ Задача не найдена или не является недельной.")
    current_days = item.get("days_of_week")
    selected = set()
    if current_days:
        selected = {int(d) for d in current_days.split(",") if d.isdigit()}
    context.user_data["edit_item_id"] = item_id
    context.user_data["edit_days_selected"] = selected
    breadcrumb = get_breadcrumb(item["location"], item["category"])
    text = f"{breadcrumb}\n\nВыберите дни недели (можно несколько):"
    await render(update, context, text, days_selection_keyboard(selected), message_id)
    return ADMIN_AWAIT_DAYS


async def handle_days_selection_for_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None
    item_id = context.user_data.get("edit_item_id")
    if not item_id:
        return await show_items_list(update, context, message_id, notice="⚠️ Ошибка: не найден ID задачи.")
    selected = context.user_data.get("edit_days_selected", set())

    if data.startswith(CB_DAY_TOGGLE_PREFIX):
        day = int(data.split(":")[1])
        if day in selected:
            selected.remove(day)
        else:
            selected.add(day)
        context.user_data["edit_days_selected"] = selected
        item = get_item(item_id)
        if item:
            breadcrumb = get_breadcrumb(item["location"], item["category"])
            text = f"{breadcrumb}\n\nВыберите дни недели (можно несколько):"
            await render(update, context, text, days_selection_keyboard(selected), message_id)
        return ADMIN_AWAIT_DAYS

    elif data == CB_DAYS_CONFIRM:
        if not selected:
            await query.answer("Выберите хотя бы один день")
            return ADMIN_AWAIT_DAYS
        days_str = ",".join(str(d) for d in sorted(selected))
        update_item_days(item_id, days_str)
        context.user_data.pop("edit_item_id", None)
        context.user_data.pop("edit_days_selected", None)
        return await show_item_detail(update, context, item_id, message_id, notice="✅ Дни обновлены.")

    elif data == CB_DAYS_CANCEL:
        context.user_data.pop("edit_item_id", None)
        context.user_data.pop("edit_days_selected", None)
        return await show_item_detail(update, context, item_id, message_id, notice="Отменено.")

    return await show_edit_locations(update, context, message_id)


async def show_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE,
                              item_id, message_id=None) -> int:
    item = get_item(item_id)
    if not item:
        return await show_items_list(update, context, message_id, notice="⚠️ Пункт не найден.")
    text = f"🗑 Удалить пункт?\n\n{item.get('text')}\n\nЭто действие нельзя отменить."
    await render(update, context, text, confirm_delete_keyboard(item_id), message_id)
    return ADMIN_DELETE_CONFIRM


async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE,
                         item_id, message_id=None) -> int:
    item = get_item(item_id)
    if not item:
        return await show_items_list(update, context, message_id, notice="⚠️ Пункт уже удалён.")
    location, category = item["location"], item["category"]
    page = context.user_data.get("edit_page", 1)
    remove_item(item_id)
    return await show_items_list(update, context, message_id, location=location,
                                 category=category, page=page, notice="🗑 Пункт удалён.")


# ==================== ОСНОВНОЙ РОУТЕР ====================
async def edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    message_id = query.message.message_id if query.message else None
    prefix, value = data.split(":", 1) if ":" in data else (data, None)

    # --- Навигация ---
    if data == CB_HOME:
        from ..menu.handlers import show_main
        return await show_main(update, context, message_id)

    if data == CB_TO_EDIT:
        return await show_edit_locations(update, context, message_id)

    if data == CB_TO_CATEGORIES:
        return await show_edit_categories(update, context, message_id)

    if data == CB_TO_ITEMS:
        return await show_items_list(update, context, message_id)

    if prefix == CB_LOC_PREFIX:
        return await show_edit_categories(update, context, message_id, location=value)

    if prefix == CB_CAT_PREFIX:
        try:
            loc, cat = value.split(":", 1)
            return await show_items_list(update, context, message_id, location=loc, category=cat, page=1)
        except ValueError:
            return await show_edit_locations(update, context, message_id)

    if prefix == CB_PAGE_PREFIX:
        try:
            loc, cat, page_s = value.split(":", 2)
            return await show_items_list(update, context, message_id, location=loc, category=cat, page=int(page_s))
        except ValueError:
            return await show_edit_locations(update, context, message_id)

    if prefix == CB_ITEM_PREFIX:
        try:
            return await show_item_detail(update, context, int(value), message_id)
        except (TypeError, ValueError):
            return await show_items_list(update, context, message_id)

    # --- Добавление ---
    if data == CB_ADD:
        return await start_add(update, context, message_id)

    if data.startswith(CB_ITEM_TYPE_PREFIX):
        return await item_type_selection(update, context)

    if data == CB_DAYS_CONFIRM or data == CB_DAYS_CANCEL or data.startswith(CB_DAY_TOGGLE_PREFIX):
        # Проверяем, в режиме редактирования ли мы (есть edit_item_id)
        if context.user_data.get("edit_item_id"):
            return await handle_days_selection_for_edit(update, context)
        else:
            return await days_selection(update, context)

    if data == CB_MONTH_PREV or data == CB_MONTH_NEXT or data.startswith(CB_DATE_PREFIX):
        return await date_selection(update, context)

    if data.startswith(CB_PHOTO_FLAG_PREFIX):
        return await photo_flag_selection(update, context)

    if data.startswith(CB_NOTIF_FLAG_PREFIX):
        return await notification_flag_selection(update, context)

    if data == CB_FLAGS_SKIP:
        context.user_data["add_requires_photo"] = False
        context.user_data["add_requires_notification"] = False
        return await finish_add(update, context, message_id)

    # --- Выбор времени ---
    if data.startswith(CB_HOUR_PREFIX):
        if context.user_data.get("edit_item_id"):
            return await handle_hour_selection_for_edit(update, context)
        else:
            return await hour_selection(update, context)

    if data.startswith(CB_MINUTE_PREFIX):
        if context.user_data.get("edit_item_id"):
            return await handle_minute_selection_for_edit(update, context)
        else:
            return await minute_selection(update, context)

    # --- Редактирование карточки ---
    if prefix == CB_EDIT_ITEM_PREFIX:
        try:
            return await prompt_edit_text(update, context, int(value), message_id)
        except (TypeError, ValueError):
            return await show_items_list(update, context, message_id)

    if prefix == CB_DELETE_ITEM_PREFIX:
        try:
            return await show_delete_confirm(update, context, int(value), message_id)
        except (TypeError, ValueError):
            return await show_items_list(update, context, message_id)

    if prefix == CB_CONFIRM_DELETE_PREFIX:
        try:
            return await confirm_delete(update, context, int(value), message_id)
        except (TypeError, ValueError):
            return await show_items_list(update, context, message_id)

    if data.startswith(CB_TOGGLE_PHOTO):
        item_id = int(value)
        return await toggle_photo(update, context, item_id, message_id)

    if data.startswith(CB_TOGGLE_NOTIFICATION):
        item_id = int(value)
        return await toggle_notification(update, context, item_id, message_id)

    if data.startswith(CB_CHANGE_TIME):
        item_id = int(value)
        return await change_time(update, context, item_id, message_id)

    if data == CB_CANCEL:
        return await cancel_action(update, context, message_id)

    if data == CB_CANCEL_EDIT:
        return await cancel_edit_text(update, context, message_id)

    if data == CB_ADD_BACK_TEXT:
        return await back_from_add_text(update, context, message_id)

    return await show_edit_locations(update, context, message_id)


# ==================== ВСПОМОГАТЕЛЬНЫЕ ====================
async def back_from_add_text(update: Update, context: ContextTypes.DEFAULT_TYPE,
                             message_id=None) -> int:
    flow = context.user_data.get("add_flow") or {}
    context.user_data.pop("await_text", None)
    return await show_items_list(update, context, message_id, location=flow.get("location"),
                                 category=flow.get("category"), page=context.user_data.get("edit_page", 1))


async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        message_id=None) -> int:
    flow = context.user_data.get("add_flow") or {}
    context.user_data.pop("await_text", None)
    context.user_data.pop("add_flow", None)
    context.user_data.pop("add_final", None)
    context.user_data.pop("add_item_type", None)
    context.user_data.pop("add_days", None)
    context.user_data.pop("add_due_date", None)
    context.user_data.pop("add_hour", None)
    context.user_data.pop("add_minute", None)
    context.user_data.pop("add_requires_photo", None)
    context.user_data.pop("add_requires_notification", None)
    context.user_data.pop("add_text", None)
    context.user_data.pop("selected_days", None)
    context.user_data.pop("edit_item_id", None)
    context.user_data.pop("edit_hour", None)
    context.user_data.pop("edit_days_selected", None)
    if flow.get("location") and flow.get("category"):
        return await show_items_list(update, context, message_id, location=flow["location"],
                                     category=flow["category"], page=context.user_data.get("edit_page", 1),
                                     notice="Отменено.")
    return await show_edit_locations(update, context, message_id, notice="Отменено.")