import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from db.users import save_user

from .constants import (
    ADMIN_MAIN, ADMIN_SHIFTS, ADMIN_CALENDAR, ADMIN_DAY_REPORT,
    ADMIN_EDIT_LOCATION, ADMIN_EDIT_CATEGORY, ADMIN_EDIT_ITEMS,
    ADMIN_ITEM_DETAIL, ADMIN_DELETE_CONFIRM,
    ADMIN_ADD_DAY, ADMIN_AWAIT_NEW_TEXT, ADMIN_AWAIT_EDIT_TEXT,
    CB_NOOP, CB_HOME, CB_SHIFTS, CB_CALENDAR, CB_EDIT,
    CB_PREV_MONTH, CB_NEXT_MONTH, CB_DAY_PREFIX,
    CB_TO_CALENDAR, CB_TO_EDIT, CB_TO_CATEGORIES, CB_TO_ITEMS,
    CB_LOC_PREFIX, CB_CAT_PREFIX, CB_PAGE_PREFIX,
    CB_ITEM_PREFIX, CB_EDIT_ITEM_PREFIX, CB_DELETE_ITEM_PREFIX,
    CB_CONFIRM_DELETE_PREFIX, CB_ADD, CB_ADD_DAY_PREFIX,
    CB_ADD_BACK_TEXT, CB_CANCEL, CB_CANCEL_EDIT,
    LOCATIONS, CATEGORY_LABELS, WEEKDAYS_SHORT, MONTHS,
    TEXT_LIMIT, MSG_LIMIT,
)

from .keyboards import (
    main_menu_keyboard, shifts_keyboard,
    calendar_keyboard, day_report_keyboard, edit_location_keyboard,
    edit_category_keyboard, items_list_keyboard, item_detail_keyboard,
    confirm_delete_keyboard, add_day_keyboard, text_prompt_keyboard,
    back_home_keyboard,
)

from .utils import (
    full_name, get_shift_days_for_month, get_day_report,
    get_location_counts, get_category_counts, get_items_for_editor,
    paginate_items, get_item, create_item, update_item_text,
    remove_item, progress_bar, percent, format_date_ru,
)

logger = logging.getLogger(__name__)


def set_state(context: ContextTypes.DEFAULT_TYPE, state: int) -> int:
    context.user_data["admin_state"] = state
    return state


def current_state(context: ContextTypes.DEFAULT_TYPE) -> int:
    return context.user_data.get("admin_state", ADMIN_MAIN)


def clear_admin_context(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in ("await_text", "add_flow", "calendar_year", "calendar_month",
                "edit_location", "edit_category", "edit_page", "last_item_id"):
        context.user_data.pop(key, None)


def clear_temp(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("await_text", None)
    context.user_data.pop("add_flow", None)


def truncate_text(text: str | None, limit: int = MSG_LIMIT) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + "…"


async def answer(query, text: str | None = None) -> None:
    try:
        await query.answer(text or "")
    except Exception:
        pass


def split_cb(data: str) -> tuple[str, str | None]:
    if ":" in data:
        prefix, value = data.split(":", 1)
        return prefix, value
    return data, None


async def render(update: Update, context: ContextTypes.DEFAULT_TYPE,
                 text: str, reply_markup=None, message_id: int | None = None) -> int | None:
    text = truncate_text(text, MSG_LIMIT)
    chat_id = update.effective_chat.id if update.effective_chat else None

    if chat_id and message_id:
        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                                text=text, reply_markup=reply_markup)
            return message_id
        except BadRequest as e:
            if "Message is not modified" in str(e):
                return message_id
            logger.warning("Edit failed: %s", e)

    if chat_id:
        msg = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
        return msg.message_id
    return None


# ==================== ЭКРАНЫ ====================

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if user:
        save_user(user.id, user.username, user.first_name, user.last_name)
    clear_admin_context(context)
    return await show_main(update, context, None)


async def show_main(update, context, message_id=None, notice=None) -> int:
    clear_admin_context(context)
    text = "🏠 Админ-панель\n\nВыберите раздел."
    if notice:
        text = f"{notice}\n\n{text}"
    await render(update, context, text, main_menu_keyboard(), message_id)
    return set_state(context, ADMIN_MAIN)


async def show_shifts(update, context, message_id=None, notice=None) -> int:
    clear_temp(context)
    # Показываем отчёт за сегодня (используем ту же функцию, что и для даты)
    today = datetime.now().strftime("%Y-%m-%d")
    return await show_day_report(update, context, today, message_id, notice)


async def show_calendar(update, context, message_id=None, notice=None) -> int:
    clear_temp(context)
    now = datetime.now()
    year = context.user_data.get("calendar_year", now.year)
    month = context.user_data.get("calendar_month", now.month)
    context.user_data["calendar_year"] = year
    context.user_data["calendar_month"] = month

    shift_days = get_shift_days_for_month(year, month)

    text = f"📅 {MONTHS[month - 1]} {year}\n\n✅ — день со сменами\nНажмите на день для отчёта."
    if notice:
        text = f"{notice}\n\n{text}"

    await render(update, context, text, calendar_keyboard(year, month, shift_days), message_id)
    return set_state(context, ADMIN_CALENDAR)


async def show_day_report(update, context, date_str, message_id=None, notice=None) -> int:
    clear_temp(context)
    report = get_day_report(date_str)

    # Формируем текст отчёта
    lines = [f"📊 Отчёт за {format_date_ru(date_str)}", ""]

    for loc_key, loc_label in LOCATIONS.items():
        loc_data = report[loc_key]
        shifts = loc_data["shifts"]
        items = loc_data["items"]
        done = loc_data["done"]
        total = loc_data["total"]
        grouped = loc_data["grouped"]

        # Сотрудники на смене
        if shifts:
            names = [full_name(s) for s in shifts]
            lines.append(f"{loc_label} · {len(shifts)} чел.: {', '.join(names)}")
        else:
            lines.append(f"{loc_label} · смен нет")

        # Прогресс
        if total > 0:
            bar = progress_bar(done, total)
            pct = percent(done, total)
            lines.append(f"Прогресс: {bar} {done}/{total} · {pct}%")
            for cat, cat_items in grouped.items():
                cat_label = CATEGORY_LABELS.get(cat, cat)
                cat_done = sum(1 for i in cat_items if i.get("completed"))
                lines.append(f"  {cat_label}: {cat_done}/{len(cat_items)}")
        else:
            lines.append("Чек-лист пуст")

        lines.append("")

    text = "\n".join(lines).strip()
    if notice:
        text = f"{notice}\n\n{text}"

    await render(update, context, text, day_report_keyboard(), message_id)
    return set_state(context, ADMIN_DAY_REPORT)


# ---------- Остальные функции (редактор) без изменений ----------
async def show_edit_locations(update, context, message_id=None, notice=None) -> int:
    clear_temp(context)
    context.user_data.pop("edit_location", None)
    context.user_data.pop("edit_category", None)
    context.user_data.pop("edit_page", None)
    counts = get_location_counts()
    text = "📝 Чек-листы\n\nВыберите локацию."
    if notice:
        text = f"{notice}\n\n{text}"
    await render(update, context, text, edit_location_keyboard(counts), message_id)
    return set_state(context, ADMIN_EDIT_LOCATION)


async def show_edit_categories(update, context, message_id=None, location=None, notice=None) -> int:
    clear_temp(context)
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
    return set_state(context, ADMIN_EDIT_CATEGORY)


async def show_items_list(update, context, message_id=None, location=None,
                          category=None, page=None, notice=None) -> int:
    clear_temp(context)
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
    return set_state(context, ADMIN_EDIT_ITEMS)


async def show_item_detail(update, context, item_id, message_id=None, notice=None) -> int:
    clear_temp(context)
    item = get_item(item_id)
    if not item:
        return await show_items_list(update, context, message_id, notice="⚠️ Пункт не найден.")
    context.user_data["edit_location"] = item["location"]
    context.user_data["edit_category"] = item["category"]
    context.user_data["last_item_id"] = item_id
    loc_label = LOCATIONS.get(item["location"], item["location"])
    cat_label = CATEGORY_LABELS.get(item["category"], item["category"])
    type_label = "ежедневный" if item["type"] == "daily" else "недельный"
    lines = ["📝 Пункт чек-листа", "", item.get("text") or "", "",
             f"Локация: {loc_label}", f"Категория: {cat_label}", f"Тип: {type_label}"]
    if item["type"] == "weekly" and item.get("day_of_week") is not None:
        lines.append(f"День: {WEEKDAYS_SHORT[item['day_of_week']]}")
    text = "\n".join(lines)
    if notice:
        text = f"{notice}\n\n{text}"
    await render(update, context, text, item_detail_keyboard(item_id), message_id)
    return set_state(context, ADMIN_ITEM_DETAIL)


async def show_delete_confirm(update, context, item_id, message_id=None) -> int:
    clear_temp(context)
    item = get_item(item_id)
    if not item:
        return await show_items_list(update, context, message_id, notice="⚠️ Пункт не найден.")
    text = f"🗑 Удалить пункт?\n\n{item.get('text')}\n\nЭто действие нельзя отменить."
    await render(update, context, text, confirm_delete_keyboard(item_id), message_id)
    return set_state(context, ADMIN_DELETE_CONFIRM)


async def confirm_delete(update, context, item_id, message_id=None) -> int:
    item = get_item(item_id)
    if not item:
        return await show_items_list(update, context, message_id, notice="⚠️ Пункт уже удалён.")
    location, category = item["location"], item["category"]
    page = context.user_data.get("edit_page", 1)
    remove_item(item_id)
    return await show_items_list(update, context, message_id, location=location,
                                 category=category, page=page, notice="🗑 Пункт удалён.")


async def prompt_edit_text(update, context, item_id, message_id=None) -> int:
    item = get_item(item_id)
    if not item:
        return await show_items_list(update, context, message_id, notice="⚠️ Пункт не найден.")
    context.user_data["last_item_id"] = item_id
    text = f"✏️ Редактирование\n\nТекущий текст:\n{item.get('text')}\n\nОтправьте новый текст обычным сообщением."
    kb = text_prompt_keyboard(CB_CANCEL_EDIT)
    new_mid = await render(update, context, text, kb, message_id)
    context.user_data["await_text"] = {"kind": "edit", "item_id": item_id,
                                       "state": ADMIN_AWAIT_EDIT_TEXT, "message_id": new_mid}
    return set_state(context, ADMIN_AWAIT_EDIT_TEXT)


async def cancel_edit_text(update, context, message_id=None) -> int:
    meta = context.user_data.get("await_text") or {}
    item_id = meta.get("item_id") or context.user_data.get("last_item_id")
    context.user_data.pop("await_text", None)
    if item_id:
        return await show_item_detail(update, context, item_id, message_id, notice="Отменено.")
    return await show_items_list(update, context, message_id, notice="Отменено.")


async def start_add(update, context, message_id=None) -> int:
    location = context.user_data.get("edit_location")
    category = context.user_data.get("edit_category")
    if location not in LOCATIONS or category not in CATEGORY_LABELS:
        return await show_edit_locations(update, context, message_id, "⚠️ Сначала выберите категорию.")
    context.user_data["add_flow"] = {"location": location, "category": category, "day_of_week": None}
    if category == "weekly":
        return await show_add_day(update, context, message_id)
    return await show_add_text(update, context, message_id)


async def show_add_day(update, context, message_id=None, notice=None) -> int:
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
    return set_state(context, ADMIN_ADD_DAY)


async def show_add_text(update, context, message_id=None, notice=None) -> int:
    flow = context.user_data.get("add_flow") or {}
    location, category, day = flow.get("location"), flow.get("category"), flow.get("day_of_week")
    if location not in LOCATIONS or category not in CATEGORY_LABELS:
        return await show_edit_locations(update, context, message_id, "⚠️ Выберите категорию заново.")
    if category == "weekly" and day is None:
        return await show_add_day(update, context, message_id)
    path = f"{LOCATIONS[location]} · {CATEGORY_LABELS[category]}"
    if category == "weekly":
        path += f" · {WEEKDAYS_SHORT[day]}"
    text = f"Новый пункт\n{path}\n\nОтправьте текст пункта обычным сообщением."
    if notice:
        text = f"{notice}\n\n{text}"
    kb = text_prompt_keyboard(CB_ADD_BACK_TEXT, CB_CANCEL)
    new_mid = await render(update, context, text, kb, message_id)
    context.user_data["await_text"] = {"kind": "new", "state": ADMIN_AWAIT_NEW_TEXT, "message_id": new_mid}
    return set_state(context, ADMIN_AWAIT_NEW_TEXT)


async def back_from_add_text(update, context, message_id=None) -> int:
    flow = context.user_data.get("add_flow") or {}
    context.user_data.pop("await_text", None)
    if flow.get("category") == "weekly":
        return await show_add_day(update, context, message_id)
    return await show_items_list(update, context, message_id, location=flow.get("location"),
                                 category=flow.get("category"), page=context.user_data.get("edit_page", 1))


async def cancel_action(update, context, message_id=None) -> int:
    flow = context.user_data.get("add_flow") or {}
    context.user_data.pop("await_text", None)
    context.user_data.pop("add_flow", None)
    if flow.get("location") and flow.get("category"):
        return await show_items_list(update, context, message_id, location=flow["location"],
                                     category=flow["category"], page=context.user_data.get("edit_page", 1),
                                     notice="Отменено.")
    return await show_edit_locations(update, context, message_id, notice="Отменено.")


# ==================== ГЛАВНЫЙ РОУТЕР ====================

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data or ""
    await answer(query)
    message_id = query.message.message_id if query.message else None
    prefix, value = split_cb(data)

    if data == CB_NOOP:
        return current_state(context)

    if data == CB_HOME:
        return await show_main(update, context, message_id)

    if data == CB_SHIFTS:
        return await show_shifts(update, context, message_id)

    if data == CB_CALENDAR:
        return await show_calendar(update, context, message_id)

    if data == CB_EDIT:
        return await show_edit_locations(update, context, message_id)

    if data == CB_PREV_MONTH:
        year = context.user_data.get("calendar_year", datetime.now().year)
        month = context.user_data.get("calendar_month", datetime.now().month)
        if month == 1:
            month, year = 12, year - 1
        else:
            month -= 1
        context.user_data.update({"calendar_year": year, "calendar_month": month})
        return await show_calendar(update, context, message_id)

    if data == CB_NEXT_MONTH:
        year = context.user_data.get("calendar_year", datetime.now().year)
        month = context.user_data.get("calendar_month", datetime.now().month)
        if month == 12:
            month, year = 1, year + 1
        else:
            month += 1
        context.user_data.update({"calendar_year": year, "calendar_month": month})
        return await show_calendar(update, context, message_id)

    if prefix == CB_DAY_PREFIX:
        try:
            date_str = datetime.strptime(value, "%Y%m%d").strftime("%Y-%m-%d")
            return await show_day_report(update, context, date_str, message_id)
        except Exception:
            return await show_calendar(update, context, message_id)

    if data == CB_TO_CALENDAR:
        return await show_calendar(update, context, message_id)

    # ---------- Редактор ----------
    if data == CB_TO_EDIT:
        return await show_edit_locations(update, context, message_id)

    if prefix == CB_LOC_PREFIX:
        return await show_edit_categories(update, context, message_id, location=value)

    if data == CB_TO_CATEGORIES:
        return await show_edit_categories(update, context, message_id)

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

    if data == CB_TO_ITEMS:
        return await show_items_list(update, context, message_id)

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

    if data == CB_ADD:
        return await start_add(update, context, message_id)

    if prefix == CB_ADD_DAY_PREFIX:
        flow = context.user_data.get("add_flow") or {}
        try:
            flow["day_of_week"] = int(value)
        except (TypeError, ValueError):
            return await show_add_day(update, context, message_id)
        context.user_data["add_flow"] = flow
        return await show_add_text(update, context, message_id)

    if data == CB_ADD_BACK_TEXT:
        return await back_from_add_text(update, context, message_id)

    if data == CB_CANCEL:
        return await cancel_action(update, context, message_id)

    if data == CB_CANCEL_EDIT:
        return await cancel_edit_text(update, context, message_id)

    return await show_main(update, context, message_id)


async def admin_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    meta = context.user_data.get("await_text")
    if not meta:
        return await show_main(update, context, None, notice="Начните заново с /start.")
    text = (update.message.text or "").strip() if update.message else ""
    message_id = meta.get("message_id")

    if not text:
        kb = text_prompt_keyboard(CB_ADD_BACK_TEXT, CB_CANCEL) if meta.get("kind") == "new" \
            else text_prompt_keyboard(CB_CANCEL_EDIT)
        await render(update, context, "⚠️ Текст не может быть пустым. Попробуйте ещё раз.", kb, message_id)
        return meta.get("state", ADMIN_MAIN)

    if len(text) > TEXT_LIMIT:
        kb = text_prompt_keyboard(CB_ADD_BACK_TEXT, CB_CANCEL) if meta.get("kind") == "new" \
            else text_prompt_keyboard(CB_CANCEL_EDIT)
        await render(update, context, f"⚠️ Слишком длинно. Максимум {TEXT_LIMIT} символов.\n\nОтправьте текст ещё раз.", kb, message_id)
        return meta.get("state", ADMIN_MAIN)

    if meta.get("kind") == "new":
        flow = context.user_data.get("add_flow") or {}
        location, category, day = flow.get("location"), flow.get("category"), flow.get("day_of_week")
        if location not in LOCATIONS or category not in CATEGORY_LABELS:
            return await show_edit_locations(update, context, message_id, "⚠️ Выберите категорию заново.")
        if category == "weekly" and day is None:
            return await show_add_day(update, context, message_id)
        item_type = "weekly" if category == "weekly" else "daily"
        create_item(item_type, location, category, day, text)
        context.user_data.pop("await_text", None)
        context.user_data.pop("add_flow", None)
        return await show_items_list(update, context, message_id, location=location,
                                     category=category, page=999999, notice="✅ Пункт добавлен.")

    if meta.get("kind") == "edit":
        item_id = meta.get("item_id")
        if not item_id:
            return await show_items_list(update, context, message_id)
        update_item_text(item_id, text)
        context.user_data.pop("await_text", None)
        return await show_item_detail(update, context, item_id, message_id, notice="✅ Сохранено.")

    return await show_main(update, context, message_id)