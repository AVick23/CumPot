from telegram import Update
from telegram.ext import ContextTypes
from .constants import (
    ADMIN_EDIT_LOCATION, ADMIN_EDIT_CATEGORY, ADMIN_EDIT_ITEMS,
    ADMIN_ITEM_DETAIL, ADMIN_DELETE_CONFIRM, ADMIN_ADD_DAY,
    ADMIN_AWAIT_NEW_TEXT, ADMIN_AWAIT_EDIT_TEXT,
    ADMIN_AWAIT_ITEM_TYPE, ADMIN_AWAIT_DUE_DATE,
    ADMIN_AWAIT_PHOTO_FLAG, ADMIN_AWAIT_NOTIFICATION_FLAG,
    CB_HOME, CB_TO_EDIT, CB_TO_CATEGORIES, CB_TO_ITEMS,
    CB_LOC_PREFIX, CB_CAT_PREFIX, CB_PAGE_PREFIX,
    CB_ITEM_PREFIX, CB_EDIT_ITEM_PREFIX, CB_DELETE_ITEM_PREFIX,
    CB_CONFIRM_DELETE_PREFIX, CB_ADD, CB_ADD_DAY_PREFIX,
    CB_ADD_BACK_TEXT, CB_CANCEL, CB_CANCEL_EDIT,
    CB_ITEM_TYPE_PREFIX, CB_DUE_DATE_BACK,
    CB_PHOTO_FLAG_PREFIX, CB_NOTIF_FLAG_PREFIX, CB_FLAGS_SKIP,
    LOCATIONS, CATEGORY_LABELS, WEEKDAYS_SHORT,
    TEXT_LIMIT,  # ← ДОБАВЛЕНО
)
from .keyboards import (
    edit_location_keyboard, edit_category_keyboard, items_list_keyboard,
    item_detail_keyboard, confirm_delete_keyboard, add_day_keyboard,
    text_prompt_keyboard, item_type_keyboard, flag_photo_keyboard,
    flag_notification_keyboard, flags_skip_keyboard,
)
from .utils import (
    get_location_counts, get_category_counts, get_items_for_editor,
    paginate_items, get_item, create_item, update_item_text, remove_item,
    render, parse_due_date,
)
import logging

logger = logging.getLogger(__name__)


async def show_edit_locations(update: Update, context: ContextTypes.DEFAULT_TYPE,
                              message_id=None, notice=None) -> int:
    context.user_data.pop("edit_location", None)
    context.user_data.pop("edit_category", None)
    context.user_data.pop("edit_page", None)
    counts = get_location_counts()
    text = "📝 Чек-листы\n\nВыберите локацию."
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
    text = f"{LOCATIONS[location]}\n\nВыберите категорию."
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
    loc_label = LOCATIONS[location]
    cat_label = CATEGORY_LABELS[category]
    header = f"{loc_label} · {cat_label}\nПунктов: {len(items)}"
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
    loc_label = LOCATIONS.get(item["location"], item["location"])
    cat_label = CATEGORY_LABELS.get(item["category"], item["category"])
    type_label = "ежедневный" if item["type"] == "daily" else "недельный" if item["type"] == "weekly" else "одноразовый"
    lines = ["📝 Пункт чек-листа", "", item.get("text") or "", "",
             f"Локация: {loc_label}", f"Категория: {cat_label}", f"Тип: {type_label}"]
    if item["type"] == "weekly" and item.get("day_of_week") is not None:
        lines.append(f"День: {WEEKDAYS_SHORT[item['day_of_week']]}")
    if item["type"] == "once" and item.get("due_date"):
        lines.append(f"Дата: {item['due_date']}")
    lines.append(f"Требуется фото: {'✅' if item.get('requires_photo') else '❌'}")
    lines.append(f"Требуется уведомление: {'✅' if item.get('requires_notification') else '❌'}")
    text = "\n".join(lines)
    if notice:
        text = f"{notice}\n\n{text}"
    await render(update, context, text, item_detail_keyboard(item_id), message_id)
    return ADMIN_ITEM_DETAIL


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


async def prompt_edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE,
                           item_id, message_id=None) -> int:
    item = get_item(item_id)
    if not item:
        return await show_items_list(update, context, message_id, notice="⚠️ Пункт не найден.")
    context.user_data["last_item_id"] = item_id
    text = f"✏️ Редактирование\n\nТекущий текст:\n{item.get('text')}\n\nОтправьте новый текст обычным сообщением."
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


# ---------- Расширенное добавление ----------
async def start_add(update: Update, context: ContextTypes.DEFAULT_TYPE,
                    message_id=None) -> int:
    location = context.user_data.get("edit_location")
    category = context.user_data.get("edit_category")
    if location not in LOCATIONS or category not in CATEGORY_LABELS:
        return await show_edit_locations(update, context, message_id, "⚠️ Сначала выберите категорию.")
    # Очищаем временные данные
    context.user_data.pop("add_flow", None)
    context.user_data.pop("add_item_type", None)
    context.user_data.pop("add_day", None)
    context.user_data.pop("add_due_date", None)
    context.user_data.pop("add_requires_photo", None)
    context.user_data.pop("add_requires_notification", None)
    # Запоминаем локацию и категорию
    context.user_data["add_flow"] = {"location": location, "category": category}
    text = f"Новый пункт для {LOCATIONS[location]} · {CATEGORY_LABELS[category]}\n\nВыберите тип задачи:"
    await render(update, context, text, item_type_keyboard(), message_id)
    return ADMIN_AWAIT_ITEM_TYPE


async def item_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None
    flow = context.user_data.get("add_flow") or {}
    location, category = flow.get("location"), flow.get("category")

    if data.startswith(CB_ITEM_TYPE_PREFIX):
        item_type = data.split(":", 1)[1]  # daily, weekly, once
        context.user_data["add_item_type"] = item_type

        if item_type == "weekly":
            # Запрашиваем день недели
            text = f"{LOCATIONS[location]} · {CATEGORY_LABELS[category]}\n\nВыберите день недели:"
            await render(update, context, text, add_day_keyboard(), message_id)
            return ADMIN_ADD_DAY
        elif item_type == "once":
            # Запрашиваем дату
            text = f"{LOCATIONS[location]} · {CATEGORY_LABELS[category]}\n\nВведите дату в формате ДД.ММ.ГГГГ или ДД-ММ-ГГГГ.\nНапример: 25.12.2025"
            kb = text_prompt_keyboard(CB_CANCEL)
            await render(update, context, text, kb, message_id)
            return ADMIN_AWAIT_DUE_DATE
        else:  # daily
            # Сразу переходим к флагам (photo/notification)
            return await ask_photo_flag(update, context, message_id)

    if data == CB_CANCEL:
        return await cancel_action(update, context, message_id)

    return await show_edit_locations(update, context, message_id)


async def due_date_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return await ask_due_date(update, context)
    text = update.message.text.strip()
    parsed = parse_due_date(text)
    if not parsed:
        await update.message.reply_text(
            "⚠️ Неверный формат даты. Используйте ДД.ММ.ГГГГ или ДД-ММ-ГГГГ.\nНапример: 25.12.2025"
        )
        return ADMIN_AWAIT_DUE_DATE
    context.user_data["add_due_date"] = parsed
    # Переходим к флагам
    return await ask_photo_flag(update, context, None, update.message.message_id)


async def ask_due_date(update: Update, context: ContextTypes.DEFAULT_TYPE,
                       message_id=None) -> int:
    flow = context.user_data.get("add_flow") or {}
    location, category = flow.get("location"), flow.get("category")
    text = f"{LOCATIONS[location]} · {CATEGORY_LABELS[category]}\n\nВведите дату в формате ДД.ММ.ГГГГ или ДД-ММ-ГГГГ.\nНапример: 25.12.2025"
    kb = text_prompt_keyboard(CB_CANCEL)
    if message_id:
        await render(update, context, text, kb, message_id)
    else:
        await render(update, context, text, kb, None)
    return ADMIN_AWAIT_DUE_DATE


async def ask_photo_flag(update: Update, context: ContextTypes.DEFAULT_TYPE,
                         message_id=None, new_message_id=None) -> int:
    flow = context.user_data.get("add_flow") or {}
    location, category = flow.get("location"), flow.get("category")
    text = f"{LOCATIONS[location]} · {CATEGORY_LABELS[category]}\n\nТребуется ли фото для этой задачи?"
    kb = flag_photo_keyboard()
    # Если есть new_message_id, редактируем его, иначе редактируем текущий message_id
    target_id = new_message_id or message_id
    await render(update, context, text, kb, target_id)
    return ADMIN_AWAIT_PHOTO_FLAG


async def photo_flag_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None

    if data.startswith(CB_PHOTO_FLAG_PREFIX):
        value = data.split(":", 1)[1]  # yes или no
        context.user_data["add_requires_photo"] = (value == "yes")
        return await ask_notification_flag(update, context, message_id)

    if data == CB_DUE_DATE_BACK:
        # Возврат к выбору типа (или к вводу даты)
        item_type = context.user_data.get("add_item_type")
        if item_type == "once":
            return await ask_due_date(update, context, message_id)
        else:
            return await start_add(update, context, message_id)

    return await start_add(update, context, message_id)


async def ask_notification_flag(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                message_id=None) -> int:
    flow = context.user_data.get("add_flow") or {}
    location, category = flow.get("location"), flow.get("category")
    text = f"{LOCATIONS[location]} · {CATEGORY_LABELS[category]}\n\nТребуется ли уведомление для этой задачи?\n(Уведомление будет отправлено всем, кто на смене в день выполнения)"
    kb = flag_notification_keyboard()
    await render(update, context, text, kb, message_id)
    return ADMIN_AWAIT_NOTIFICATION_FLAG


async def notification_flag_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None

    if data.startswith(CB_NOTIF_FLAG_PREFIX):
        value = data.split(":", 1)[1]  # yes или no
        context.user_data["add_requires_notification"] = (value == "yes")
        # Все данные собраны, создаём задачу
        return await finish_add(update, context, message_id)

    if data == CB_DUE_DATE_BACK:
        # Возврат к выбору photo
        return await ask_photo_flag(update, context, message_id)

    return await start_add(update, context, message_id)


async def finish_add(update: Update, context: ContextTypes.DEFAULT_TYPE,
                     message_id=None) -> int:
    flow = context.user_data.get("add_flow") or {}
    location = flow.get("location")
    category = flow.get("category")
    item_type = context.user_data.get("add_item_type")
    day_of_week = context.user_data.get("add_day")
    due_date = context.user_data.get("add_due_date")
    requires_photo = context.user_data.get("add_requires_photo", False)
    requires_notification = context.user_data.get("add_requires_notification", False)

    # Для once is_recurring=False, для daily/weekly is_recurring=True
    is_recurring = (item_type != "once")

    if item_type == "weekly" and day_of_week is None:
        return await show_add_day(update, context, message_id, notice="⚠️ Выберите день недели.")
    if item_type == "once" and not due_date:
        return await ask_due_date(update, context, message_id, notice="⚠️ Укажите дату.")

    # Переходим к вводу текста
    context.user_data["await_text"] = {
        "kind": "new",
        "state": ADMIN_AWAIT_NEW_TEXT,
        "message_id": message_id
    }
    # Сохраняем данные для создания
    context.user_data["add_final"] = {
        "item_type": item_type,
        "location": location,
        "category": category,
        "day_of_week": day_of_week,
        "due_date": due_date,
        "requires_photo": requires_photo,
        "requires_notification": requires_notification,
        "is_recurring": is_recurring,
    }
    text = f"Новый пункт для {LOCATIONS[location]} · {CATEGORY_LABELS[category]}\n\nОтправьте текст пункта обычным сообщением."
    kb = text_prompt_keyboard(CB_ADD_BACK_TEXT, CB_CANCEL)
    new_mid = await render(update, context, text, kb, message_id)
    # Обновим message_id в await_text
    context.user_data["await_text"]["message_id"] = new_mid
    return ADMIN_AWAIT_NEW_TEXT


async def show_add_day(update: Update, context: ContextTypes.DEFAULT_TYPE,
                       message_id=None, notice=None) -> int:
    flow = context.user_data.get("add_flow") or {}
    location = flow.get("location") or context.user_data.get("edit_location")
    category = flow.get("category") or context.user_data.get("edit_category")
    if location not in LOCATIONS or category != "weekly":
        return await show_items_list(update, context, message_id, location=location, category=category)
    context.user_data["add_flow"] = {"location": location, "category": category,
                                     "day_of_week": flow.get("day_of_week")}
    text = f"Новый пункт\n{LOCATIONS[location]} · {CATEGORY_LABELS[category]}\n\nВыберите день недели."
    if notice:
        text = f"{notice}\n\n{text}"
    await render(update, context, text, add_day_keyboard(flow.get("day_of_week")), message_id)
    return ADMIN_ADD_DAY


# ---------- Обработчики для callback'ов ----------
async def edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    message_id = query.message.message_id if query.message else None
    prefix, value = data.split(":", 1) if ":" in data else (data, None)

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

    # ---------- Расширенное добавление ----------
    if data == CB_ADD:
        return await start_add(update, context, message_id)

    if prefix == CB_ADD_DAY_PREFIX:
        # Обработка выбора дня для weekly
        flow = context.user_data.get("add_flow") or {}
        try:
            day = int(value)
        except ValueError:
            return await show_add_day(update, context, message_id)
        flow["day_of_week"] = day
        context.user_data["add_flow"] = flow
        context.user_data["add_day"] = day
        # Переходим к флагам (или к выбору типа, если это часть расширенного добавления)
        # Если мы в режиме расширенного добавления (add_item_type существует), переходим к флагам
        if context.user_data.get("add_item_type"):
            return await ask_photo_flag(update, context, message_id)
        else:
            # старое поведение (для совместимости)
            return await show_add_text(update, context, message_id)

    if data == CB_ADD_BACK_TEXT:
        return await back_from_add_text(update, context, message_id)

    if data == CB_CANCEL:
        return await cancel_action(update, context, message_id)

    if data == CB_CANCEL_EDIT:
        return await cancel_edit_text(update, context, message_id)

    # Обработка выбора типа задачи
    if data.startswith(CB_ITEM_TYPE_PREFIX):
        return await item_type_selection(update, context)

    # Обработка флага фото
    if data.startswith(CB_PHOTO_FLAG_PREFIX):
        return await photo_flag_selection(update, context)

    # Обработка флага уведомления
    if data.startswith(CB_NOTIF_FLAG_PREFIX):
        return await notification_flag_selection(update, context)

    if data == CB_DUE_DATE_BACK:
        # Возврат к выбору типа
        return await start_add(update, context, message_id)

    if data == CB_FLAGS_SKIP:
        # Пропустить настройку флагов (установить false)
        context.user_data["add_requires_photo"] = False
        context.user_data["add_requires_notification"] = False
        return await finish_add(update, context, message_id)

    return await show_edit_locations(update, context, message_id)


async def edit_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    meta = context.user_data.get("await_text")
    if not meta:
        return await show_edit_locations(update, context, None, notice="Начните заново с /start.")
    text = (update.message.text or "").strip() if update.message else ""
    message_id = meta.get("message_id")

    if not text:
        kb = text_prompt_keyboard(CB_ADD_BACK_TEXT, CB_CANCEL) if meta.get("kind") == "new" \
            else text_prompt_keyboard(CB_CANCEL_EDIT)
        await render(update, context, "⚠️ Текст не может быть пустым. Попробуйте ещё раз.", kb, message_id)
        return meta.get("state", ADMIN_EDIT_LOCATION)

    if len(text) > TEXT_LIMIT:
        kb = text_prompt_keyboard(CB_ADD_BACK_TEXT, CB_CANCEL) if meta.get("kind") == "new" \
            else text_prompt_keyboard(CB_CANCEL_EDIT)
        await render(update, context, f"⚠️ Слишком длинно. Максимум {TEXT_LIMIT} символов.\n\nОтправьте текст ещё раз.", kb, message_id)
        return meta.get("state", ADMIN_EDIT_LOCATION)

    if meta.get("kind") == "new":
        # Создаём задачу с данными из add_final
        final_data = context.user_data.get("add_final") or {}
        if not final_data:
            return await show_edit_locations(update, context, message_id, "Ошибка: данные не найдены.")
        create_item(
            item_type=final_data["item_type"],
            location=final_data["location"],
            category=final_data["category"],
            day_of_week=final_data.get("day_of_week"),
            text=text,
            requires_photo=final_data.get("requires_photo", False),
            requires_notification=final_data.get("requires_notification", False),
            due_date=final_data.get("due_date"),
            is_recurring=final_data.get("is_recurring", True)
        )
        context.user_data.pop("await_text", None)
        context.user_data.pop("add_flow", None)
        context.user_data.pop("add_final", None)
        context.user_data.pop("add_item_type", None)
        context.user_data.pop("add_day", None)
        context.user_data.pop("add_due_date", None)
        context.user_data.pop("add_requires_photo", None)
        context.user_data.pop("add_requires_notification", None)
        return await show_items_list(update, context, message_id, location=final_data["location"],
                                     category=final_data["category"], page=999999, notice="✅ Пункт добавлен.")

    if meta.get("kind") == "edit":
        item_id = meta.get("item_id")
        if not item_id:
            return await show_items_list(update, context, message_id)
        update_item_text(item_id, text)
        context.user_data.pop("await_text", None)
        return await show_item_detail(update, context, item_id, message_id, notice="✅ Сохранено.")

    return await show_edit_locations(update, context, message_id)


# ---------- Вспомогательные функции для совместимости ----------
async def back_from_add_text(update: Update, context: ContextTypes.DEFAULT_TYPE,
                             message_id=None) -> int:
    flow = context.user_data.get("add_flow") or {}
    context.user_data.pop("await_text", None)
    if flow.get("category") == "weekly":
        return await show_add_day(update, context, message_id)
    return await show_items_list(update, context, message_id, location=flow.get("location"),
                                 category=flow.get("category"), page=context.user_data.get("edit_page", 1))


async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE,
                        message_id=None) -> int:
    flow = context.user_data.get("add_flow") or {}
    context.user_data.pop("await_text", None)
    context.user_data.pop("add_flow", None)
    context.user_data.pop("add_final", None)
    context.user_data.pop("add_item_type", None)
    context.user_data.pop("add_day", None)
    context.user_data.pop("add_due_date", None)
    context.user_data.pop("add_requires_photo", None)
    context.user_data.pop("add_requires_notification", None)
    if flow.get("location") and flow.get("category"):
        return await show_items_list(update, context, message_id, location=flow["location"],
                                     category=flow["category"], page=context.user_data.get("edit_page", 1),
                                     notice="Отменено.")
    return await show_edit_locations(update, context, message_id, notice="Отменено.")