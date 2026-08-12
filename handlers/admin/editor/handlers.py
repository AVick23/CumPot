import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from .constants import (
    ADMIN_EDIT_LOCATION,
    ADMIN_EDIT_CATEGORY,
    ADMIN_EDIT_ITEMS,
    ADMIN_ITEM_DETAIL,
    ADMIN_DELETE_CONFIRM,
    ADMIN_AWAIT_NEW_TEXT,
    ADMIN_AWAIT_EDIT_TEXT,
    ADMIN_AWAIT_DATE,
    ADMIN_AWAIT_HOUR,
    ADMIN_AWAIT_MINUTE,
    ADMIN_AWAIT_PHOTO_FLAG,
    ADMIN_AWAIT_NOTIFICATION_FLAG,
    ADMIN_AWAIT_DAYS,
    CB_HOME,
    CB_TO_EDIT,
    CB_TO_CATEGORIES,
    CB_TO_ITEMS,
    CB_LOC_PREFIX,
    CB_CAT_PREFIX,
    CB_PAGE_PREFIX,
    CB_ITEM_PREFIX,
    CB_EDIT_ITEM_PREFIX,
    CB_DELETE_ITEM_PREFIX,
    CB_CONFIRM_DELETE_PREFIX,
    CB_ADD,
    CB_ADD_PICK,
    CB_CANCEL,
    CB_CANCEL_EDIT,
    CB_ADD_BACK_TEXT,
    CB_DATE_PREFIX,
    CB_MONTH_PREV,
    CB_MONTH_NEXT,
    CB_HOUR_PREFIX,
    CB_MINUTE_PREFIX,
    CB_PHOTO_FLAG_PREFIX,
    CB_NOTIF_FLAG_PREFIX,
    CB_TOGGLE_PHOTO,
    CB_TOGGLE_NOTIFICATION,
    CB_CHANGE_TIME,
    CB_CHANGE_DATE,
    CB_ADD_DAY_PREFIX,
    CB_DAY_TOGGLE_PREFIX,
    CB_DAY_PRESET_PREFIX,
    CB_DAYS_SAVE,
    CB_DAYS_CANCEL,
    LOCATIONS,
    CATEGORY_LABELS,
    WEEKDAYS_SHORT,
    TEXT_LIMIT,
)

from .keyboards import (
    edit_location_keyboard,
    edit_category_keyboard,
    items_list_keyboard,
    item_detail_keyboard,
    confirm_delete_keyboard,
    text_prompt_keyboard,
    days_selection_keyboard,
    calendar_keyboard,
    hour_keyboard,
    minute_keyboard,
    flag_photo_keyboard,
    flag_notification_keyboard,
)

from .utils import (
    get_location_counts,
    get_category_counts,
    get_items_for_editor,
    paginate_items,
    get_item,
    create_item,
    update_item_text,
    update_item_flags,
    update_item_days,
    update_item_due_date,
    remove_item,
    render,
    get_breadcrumb,
    type_for_category,
    get_week_days,
    format_date_ru,
)

logger = logging.getLogger(__name__)


# =========================================================
# HELPERS
# =========================================================

def _state(context: ContextTypes.DEFAULT_TYPE, state: int) -> int:
    context.user_data["ui_state"] = state
    return state


def _current_state(context: ContextTypes.DEFAULT_TYPE, default: int = ADMIN_EDIT_LOCATION) -> int:
    return context.user_data.get("ui_state", default)


_ADD_KEYS = (
    "add_in_progress",
    "add_flow",
    "add_type",
    "selected_days",
    "add_days",
    "add_due_date",
    "add_hour",
    "add_minute",
    "add_requires_photo",
    "add_requires_notification",
    "add_text",
    "await_text",
    "calendar_year",
    "calendar_month",
    "add_location",
)

_EDIT_KEYS = (
    "edit_item_id",
    "edit_hour",
    "edit_days_selected",
    "edit_date_mode",
    "edit_new_notification",
)


def _clear_add_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in _ADD_KEYS:
        context.user_data.pop(key, None)


def _clear_edit_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in _EDIT_KEYS:
        context.user_data.pop(key, None)


def _clear_all_editor(context: ContextTypes.DEFAULT_TYPE) -> None:
    _clear_add_state(context)
    _clear_edit_state(context)

    for key in (
        "edit_location",
        "edit_category",
        "edit_page",
        "last_item_id",
        "ui_state",
    ):
        context.user_data.pop(key, None)


def _text_keyboard_for_meta(meta: dict):
    if meta.get("kind") == "edit":
        return text_prompt_keyboard(CB_CANCEL_EDIT)

    return text_prompt_keyboard(CB_ADD_BACK_TEXT, CB_CANCEL)


# =========================================================
# NAVIGATION SCREENS
# =========================================================

async def show_edit_locations(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
    notice=None,
) -> int:
    context.user_data.pop("edit_location", None)
    context.user_data.pop("edit_category", None)
    context.user_data.pop("edit_page", None)

    counts = get_location_counts()

    text = "Редактор чек-листов\n\nВыберите локацию."

    if notice:
        text = f"{notice}\n\n{text}"

    await render(
        update,
        context,
        text,
        edit_location_keyboard(counts),
        message_id,
    )

    return _state(context, ADMIN_EDIT_LOCATION)


async def show_edit_categories(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
    location=None,
    notice=None,
) -> int:
    location = location or context.user_data.get("edit_location")

    if location not in LOCATIONS:
        return await show_edit_locations(
            update,
            context,
            message_id,
            "Сначала выберите локацию.",
        )

    context.user_data["edit_location"] = location
    context.user_data.pop("edit_category", None)
    context.user_data.pop("edit_page", None)

    counts = get_category_counts(location)

    text = f"{LOCATIONS.get(location)}\n\nВыберите раздел."

    if notice:
        text = f"{notice}\n\n{text}"

    await render(
        update,
        context,
        text,
        edit_category_keyboard(location, counts),
        message_id,
    )

    return _state(context, ADMIN_EDIT_CATEGORY)


async def show_items_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
    location=None,
    category=None,
    page=None,
    notice=None,
) -> int:
    location = location or context.user_data.get("edit_location")
    category = category or context.user_data.get("edit_category")

    if location not in LOCATIONS:
        return await show_edit_locations(
            update,
            context,
            message_id,
            "Сначала выберите локацию.",
        )

    if category not in CATEGORY_LABELS:
        return await show_edit_categories(
            update,
            context,
            message_id,
            location,
            "Сначала выберите раздел.",
        )

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

    if page_items:
        header += "\n\nНажмите на пункт, чтобы открыть."
    else:
        header += "\n\nПока пусто. Добавьте первый пункт."

    if notice:
        header = f"{notice}\n\n{header}"

    await render(
        update,
        context,
        header,
        items_list_keyboard(location, category, page_items, page, total_pages),
        message_id,
    )

    return _state(context, ADMIN_EDIT_ITEMS)


async def show_item_detail(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    item_id: int,
    message_id=None,
    notice=None,
) -> int:
    item = get_item(item_id)

    if not item:
        return await show_items_list(
            update,
            context,
            message_id,
            notice="Пункт не найден.",
        )

    context.user_data["edit_location"] = item.get("location")
    context.user_data["edit_category"] = item.get("category")
    context.user_data["last_item_id"] = item_id

    breadcrumb = get_breadcrumb(item.get("location"), item.get("category"))

    loc_label = LOCATIONS.get(item.get("location"), item.get("location"))
    cat_label = CATEGORY_LABELS.get(item.get("category"), item.get("category"))

    item_type = item.get("type") or "daily"

    type_labels = {
        "daily": "Ежедневно",
        "weekly": "По дням недели",
        "once": "Один раз",
    }

    type_label = type_labels.get(item_type, item_type)

    lines = [
        breadcrumb,
        "",
        item.get("text") or "",
        "",
        f"Локация: {loc_label}",
        f"Раздел: {cat_label}",
        f"Повтор: {type_label}",
    ]

    if item_type == "weekly":
        days = get_week_days(item)
        if days:
            days_label = ", ".join(WEEKDAYS_SHORT[d] for d in days)
        else:
            days_label = "не выбраны"
        lines.append(f"Дни: {days_label}")

    elif item_type == "once" and item.get("due_date"):
        lines.append(f"Дата: {format_date_ru(item.get('due_date'))}")

    lines.append(f"Фото: {'Вкл' if item.get('requires_photo') else 'Выкл'}")
    lines.append(f"Уведомление: {'Вкл' if item.get('requires_notification') else 'Выкл'}")

    if item.get("requires_notification") and item.get("notification_time"):
        lines.append(f"Время уведомления: {item.get('notification_time')}")

    text = "\n".join(lines)

    if notice:
        text = f"{notice}\n\n{text}"

    await render(
        update,
        context,
        text,
        item_detail_keyboard(item),
        message_id,
    )

    return _state(context, ADMIN_ITEM_DETAIL)


async def show_delete_confirm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    item_id: int,
    message_id=None,
) -> int:
    item = get_item(item_id)

    if not item:
        return await show_items_list(
            update,
            context,
            message_id,
            notice="Пункт не найден.",
        )

    text = (
        "Удалить пункт?\n\n"
        f"{item.get('text')}\n\n"
        "Это действие нельзя отменить."
    )

    await render(
        update,
        context,
        text,
        confirm_delete_keyboard(item_id),
        message_id,
    )

    return _state(context, ADMIN_DELETE_CONFIRM)


# =========================================================
# ADD FLOW: SCREENS
# =========================================================

async def start_add(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
) -> int:
    _clear_add_state(context)

    location = context.user_data.get("edit_location")
    category = context.user_data.get("edit_category")

    if location not in LOCATIONS:
        context.user_data["add_in_progress"] = True
        return await show_edit_locations(
            update,
            context,
            message_id,
            notice="Новая задача\n\nСначала выберите локацию.",
        )

    if category not in CATEGORY_LABELS:
        context.user_data["add_in_progress"] = True
        return await show_edit_categories(
            update,
            context,
            message_id,
            location=location,
            notice="Новая задача\n\nТеперь выберите раздел.",
        )

    context.user_data.pop("add_in_progress", None)
    context.user_data["add_flow"] = {
        "location": location,
        "category": category,
    }
    context.user_data["selected_days"] = set()

    if category == "weekly":
        return await ask_days(update, context, message_id)

    if category == "once":
        return await ask_date(update, context, message_id)

    return await ask_text(update, context, message_id)


async def ask_days(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
) -> int:
    flow = context.user_data.get("add_flow") or {}
    location = flow.get("location")
    category = flow.get("category")

    if location not in LOCATIONS or category not in CATEGORY_LABELS:
        return await show_edit_locations(
            update,
            context,
            message_id,
            notice="Начните добавление заново.",
        )

    if "selected_days" not in context.user_data:
        context.user_data["selected_days"] = set()

    breadcrumb = get_breadcrumb(location, category)
    text = f"{breadcrumb}\n\nВыберите дни недели. Можно несколько."

    await render(
        update,
        context,
        text,
        days_selection_keyboard(context.user_data.get("selected_days", set())),
        message_id,
    )

    return _state(context, ADMIN_AWAIT_DAYS)


async def ask_date(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
) -> int:
    flow = context.user_data.get("add_flow") or {}
    location = flow.get("location")
    category = flow.get("category")

    if location not in LOCATIONS or category not in CATEGORY_LABELS:
        return await show_edit_locations(
            update,
            context,
            message_id,
            notice="Начните добавление заново.",
        )

    now = datetime.now()

    year = context.user_data.get("calendar_year", now.year)
    month = context.user_data.get("calendar_month", now.month)

    context.user_data["calendar_year"] = year
    context.user_data["calendar_month"] = month

    breadcrumb = get_breadcrumb(location, category)
    text = f"{breadcrumb}\n\nВыберите дату."

    await render(
        update,
        context,
        text,
        calendar_keyboard(year, month, context.user_data.get("add_due_date")),
        message_id,
    )

    return _state(context, ADMIN_AWAIT_DATE)


async def ask_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
) -> int:
    flow = context.user_data.get("add_flow") or {}
    location = flow.get("location")
    category = flow.get("category")

    if location not in LOCATIONS or category not in CATEGORY_LABELS:
        return await show_edit_locations(
            update,
            context,
            message_id,
            notice="Начните добавление заново.",
        )

    breadcrumb = get_breadcrumb(location, category)
    text = f"{breadcrumb}\n\nОтправьте текст задачи обычным сообщением."

    kb = text_prompt_keyboard(CB_ADD_BACK_TEXT, CB_CANCEL)

    new_message_id = await render(
        update,
        context,
        text,
        kb,
        message_id,
    )

    context.user_data["await_text"] = {
        "kind": "new",
        "state": ADMIN_AWAIT_NEW_TEXT,
        "message_id": new_message_id,
    }

    return _state(context, ADMIN_AWAIT_NEW_TEXT)


async def ask_photo_flag(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
) -> int:
    flow = context.user_data.get("add_flow") or {}
    location = flow.get("location")
    category = flow.get("category")

    if location not in LOCATIONS or category not in CATEGORY_LABELS:
        return await show_edit_locations(
            update,
            context,
            message_id,
            notice="Начните добавление заново.",
        )

    breadcrumb = get_breadcrumb(location, category)
    text = f"{breadcrumb}\n\nНужно ли прикреплять фото к этой задаче?"

    await render(
        update,
        context,
        text,
        flag_photo_keyboard(),
        message_id,
    )

    return _state(context, ADMIN_AWAIT_PHOTO_FLAG)


async def ask_notification_flag(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
) -> int:
    flow = context.user_data.get("add_flow") or {}
    location = flow.get("location")
    category = flow.get("category")

    if location not in LOCATIONS or category not in CATEGORY_LABELS:
        return await show_edit_locations(
            update,
            context,
            message_id,
            notice="Начните добавление заново.",
        )

    breadcrumb = get_breadcrumb(location, category)
    text = (
        f"{breadcrumb}\n\n"
        "Нужно ли уведомление?\n"
        "Оно придёт в день выполнения задачи."
    )

    await render(
        update,
        context,
        text,
        flag_notification_keyboard(),
        message_id,
    )

    return _state(context, ADMIN_AWAIT_NOTIFICATION_FLAG)


async def _show_hour_picker(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id,
    text: str,
) -> int:
    await render(
        update,
        context,
        text,
        hour_keyboard(),
        message_id,
    )

    return _state(context, ADMIN_AWAIT_HOUR)


async def _show_minute_picker(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id,
    text: str,
) -> int:
    await render(
        update,
        context,
        text,
        minute_keyboard(),
        message_id,
    )

    return _state(context, ADMIN_AWAIT_MINUTE)


async def ask_hour(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
) -> int:
    flow = context.user_data.get("add_flow") or {}
    location = flow.get("location")
    category = flow.get("category")

    if location not in LOCATIONS or category not in CATEGORY_LABELS:
        return await show_edit_locations(
            update,
            context,
            message_id,
            notice="Начните добавление заново.",
        )

    breadcrumb = get_breadcrumb(location, category)
    text = f"{breadcrumb}\n\nВыберите час уведомления."

    return await _show_hour_picker(update, context, message_id, text)


async def ask_minute(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
) -> int:
    flow = context.user_data.get("add_flow") or {}
    location = flow.get("location")
    category = flow.get("category")

    if location not in LOCATIONS or category not in CATEGORY_LABELS:
        return await show_edit_locations(
            update,
            context,
            message_id,
            notice="Начните добавление заново.",
        )

    breadcrumb = get_breadcrumb(location, category)
    text = f"{breadcrumb}\n\nВыберите минуты."

    return await _show_minute_picker(update, context, message_id, text)


async def _render_edit_calendar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
) -> int:
    item_id = context.user_data.get("edit_item_id")
    item = get_item(item_id)

    if not item:
        _clear_edit_state(context)
        return await show_items_list(
            update,
            context,
            message_id,
            notice="Пункт не найден.",
        )

    now = datetime.now()

    year = context.user_data.get("calendar_year", now.year)
    month = context.user_data.get("calendar_month", now.month)

    context.user_data["calendar_year"] = year
    context.user_data["calendar_month"] = month

    breadcrumb = get_breadcrumb(item.get("location"), item.get("category"))
    text = f"{breadcrumb}\n\nВыберите новую дату."

    await render(
        update,
        context,
        text,
        calendar_keyboard(year, month, item.get("due_date")),
        message_id,
    )

    return _state(context, ADMIN_AWAIT_DATE)


async def _render_edit_days(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id,
    item: dict,
    selected: set[int],
    notice=None,
) -> int:
    breadcrumb = get_breadcrumb(item.get("location"), item.get("category"))
    text = f"{breadcrumb}\n\nВыберите дни недели. Можно несколько."

    if notice:
        text = f"{notice}\n\n{text}"

    await render(
        update,
        context,
        text,
        days_selection_keyboard(selected),
        message_id,
    )

    return _state(context, ADMIN_AWAIT_DAYS)


# =========================================================
# ADD FLOW: HANDLERS
# =========================================================

async def days_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None

    # Если редактируем уже существующую weekly-задачу
    if context.user_data.get("edit_item_id"):
        return await handle_days_selection_for_edit(update, context)

    flow = context.user_data.get("add_flow") or {}
    location = flow.get("location")
    category = flow.get("category")

    if location not in LOCATIONS or category not in CATEGORY_LABELS:
        return await show_edit_locations(
            update,
            context,
            message_id,
            notice="Начните добавление заново.",
        )

    selected = context.user_data.get("selected_days", set())

    if data.startswith(f"{CB_DAY_TOGGLE_PREFIX}:"):
        day = int(data.split(":", 1)[1])

        if day in selected:
            selected.remove(day)
        else:
            selected.add(day)

        context.user_data["selected_days"] = selected
        return await ask_days(update, context, message_id)

    if data.startswith(f"{CB_DAY_PRESET_PREFIX}:"):
        preset = data.split(":", 1)[1]

        if preset == "all":
            selected = set(range(7))
        elif preset == "weekdays":
            selected = set(range(5))
        elif preset == "weekend":
            selected = {5, 6}
        else:
            selected = set()

        context.user_data["selected_days"] = selected
        return await ask_days(update, context, message_id)

    if data == CB_DAYS_SAVE:
        if not selected:
            await query.answer("Выберите хотя бы один день", show_alert=True)
            return _state(context, ADMIN_AWAIT_DAYS)

        await query.answer()

        days_str = ",".join(str(d) for d in sorted(selected))
        context.user_data["add_days"] = days_str

        return await ask_text(update, context, message_id)

    if data == CB_DAYS_CANCEL:
        return await cancel_action(update, context, message_id)

    return _state(context, ADMIN_AWAIT_DAYS)


async def handle_days_selection_for_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None

    item_id = context.user_data.get("edit_item_id")

    if not item_id:
        return await show_items_list(
            update,
            context,
            message_id,
            notice="Пункт не найден.",
        )

    item = get_item(item_id)

    if not item:
        _clear_edit_state(context)
        return await show_items_list(
            update,
            context,
            message_id,
            notice="Пункт не найден.",
        )

    selected = context.user_data.get("edit_days_selected", set())

    if data.startswith(f"{CB_DAY_TOGGLE_PREFIX}:"):
        day = int(data.split(":", 1)[1])

        if day in selected:
            selected.remove(day)
        else:
            selected.add(day)

        context.user_data["edit_days_selected"] = selected
        return await _render_edit_days(update, context, message_id, item, selected)

    if data.startswith(f"{CB_DAY_PRESET_PREFIX}:"):
        preset = data.split(":", 1)[1]

        if preset == "all":
            selected = set(range(7))
        elif preset == "weekdays":
            selected = set(range(5))
        elif preset == "weekend":
            selected = {5, 6}
        else:
            selected = set()

        context.user_data["edit_days_selected"] = selected
        return await _render_edit_days(update, context, message_id, item, selected)

    if data == CB_DAYS_SAVE:
        if not selected:
            await query.answer("Выберите хотя бы один день", show_alert=True)
            return _state(context, ADMIN_AWAIT_DAYS)

        await query.answer()

        days_str = ",".join(str(d) for d in sorted(selected))
        update_item_days(item_id, days_str)

        _clear_edit_state(context)

        return await show_item_detail(
            update,
            context,
            item_id,
            message_id,
            notice="Дни обновлены.",
        )

    if data == CB_DAYS_CANCEL:
        _clear_edit_state(context)

        return await show_item_detail(
            update,
            context,
            item_id,
            message_id,
            notice="Отменено.",
        )

    return _state(context, ADMIN_AWAIT_DAYS)


async def date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None

    edit_mode = bool(
        context.user_data.get("edit_date_mode") and context.user_data.get("edit_item_id")
    )

    if data in (CB_MONTH_PREV, CB_MONTH_NEXT):
        now = datetime.now()

        year = context.user_data.get("calendar_year", now.year)
        month = context.user_data.get("calendar_month", now.month)

        if data == CB_MONTH_PREV:
            if month == 1:
                month = 12
                year -= 1
            else:
                month -= 1
        else:
            if month == 12:
                month = 1
                year += 1
            else:
                month += 1

        context.user_data["calendar_year"] = year
        context.user_data["calendar_month"] = month

        if edit_mode:
            return await _render_edit_calendar(update, context, message_id)

        return await ask_date(update, context, message_id)

    if data.startswith(f"{CB_DATE_PREFIX}:"):
        date_str = data.split(":", 1)[1]

        if edit_mode:
            item_id = context.user_data.get("edit_item_id")
            update_item_due_date(item_id, date_str)
            _clear_edit_state(context)

            return await show_item_detail(
                update,
                context,
                item_id,
                message_id,
                notice="Дата обновлена.",
            )

        context.user_data["add_due_date"] = date_str
        return await ask_text(update, context, message_id)

    return _state(context, ADMIN_AWAIT_DATE)


async def photo_flag_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None

    if data.startswith(f"{CB_PHOTO_FLAG_PREFIX}:"):
        value = data.split(":", 1)[1]
        context.user_data["add_requires_photo"] = value == "yes"
        return await ask_notification_flag(update, context, message_id)

    return _current_state(context)


async def notification_flag_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None

    if data.startswith(f"{CB_NOTIF_FLAG_PREFIX}:"):
        value = data.split(":", 1)[1]
        context.user_data["add_requires_notification"] = value == "yes"

        if context.user_data.get("add_requires_notification"):
            return await ask_hour(update, context, message_id)

        return await finish_add(update, context, message_id)

    return _current_state(context)


async def hour_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None

    if context.user_data.get("edit_item_id"):
        return await handle_hour_selection_for_edit(update, context)

    if data.startswith(f"{CB_HOUR_PREFIX}:"):
        hour = int(data.split(":", 1)[1])
        context.user_data["add_hour"] = hour
        return await ask_minute(update, context, message_id)

    return _state(context, ADMIN_AWAIT_HOUR)


async def minute_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None

    if context.user_data.get("edit_item_id"):
        return await handle_minute_selection_for_edit(update, context)

    if data.startswith(f"{CB_MINUTE_PREFIX}:"):
        minute = int(data.split(":", 1)[1])
        context.user_data["add_minute"] = minute
        return await finish_add(update, context, message_id)

    return _state(context, ADMIN_AWAIT_MINUTE)


async def handle_hour_selection_for_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None

    item_id = context.user_data.get("edit_item_id")

    if not item_id:
        return await show_items_list(
            update,
            context,
            message_id,
            notice="Пункт не найден.",
        )

    if data.startswith(f"{CB_HOUR_PREFIX}:"):
        hour = int(data.split(":", 1)[1])
        context.user_data["edit_hour"] = hour

        item = get_item(item_id)
        breadcrumb = get_breadcrumb(item.get("location"), item.get("category")) if item else ""
        text = f"{breadcrumb}\n\nВыберите минуты." if breadcrumb else "Выберите минуты."

        return await _show_minute_picker(update, context, message_id, text)

    return _state(context, ADMIN_AWAIT_HOUR)


async def handle_minute_selection_for_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None

    item_id = context.user_data.get("edit_item_id")

    if not item_id:
        return await show_items_list(
            update,
            context,
            message_id,
            notice="Пункт не найден.",
        )

    if data.startswith(f"{CB_MINUTE_PREFIX}:"):
        minute = int(data.split(":", 1)[1])
        hour = context.user_data.get("edit_hour")

        if hour is None:
            return await show_item_detail(
                update,
                context,
                item_id,
                message_id,
                notice="Сначала выберите час.",
            )

        notification_time = f"{hour:02d}:{minute:02d}"

        update_item_flags(
            item_id,
            requires_notification=True,
            notification_time=notification_time,
        )

        _clear_edit_state(context)

        return await show_item_detail(
            update,
            context,
            item_id,
            message_id,
            notice=f"Время уведомления обновлено: {notification_time}",
        )

    return _state(context, ADMIN_AWAIT_MINUTE)


async def finish_add(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
) -> int:
    flow = context.user_data.get("add_flow") or {}

    location = flow.get("location")
    category = flow.get("category")

    if location not in LOCATIONS or category not in CATEGORY_LABELS:
        return await show_edit_locations(
            update,
            context,
            message_id,
            notice="Начните добавление заново.",
        )

    item_type = type_for_category(category)
    text = context.user_data.get("add_text")

    if not text:
        return await ask_text(update, context, message_id)

    days_str = None
    due_date = None
    day_of_week = None

    if item_type == "weekly":
        days_str = context.user_data.get("add_days")

        if not days_str:
            return await ask_days(update, context, message_id)

        first_day = int(days_str.split(",")[0])
        day_of_week = first_day

    elif item_type == "once":
        due_date = context.user_data.get("add_due_date")

        if not due_date:
            return await ask_date(update, context, message_id)

    requires_photo = bool(context.user_data.get("add_requires_photo", False))
    requires_notification = bool(context.user_data.get("add_requires_notification", False))

    hour = context.user_data.get("add_hour")
    minute = context.user_data.get("add_minute")

    notification_time = None

    if requires_notification:
        if hour is None or minute is None:
            return await ask_hour(update, context, message_id)

        notification_time = f"{hour:02d}:{minute:02d}"

    create_item(
        item_type=item_type,
        location=location,
        category=category,
        day_of_week=day_of_week,
        text=text,
        requires_photo=requires_photo,
        requires_notification=requires_notification,
        notification_time=notification_time,
        due_date=due_date,
        is_recurring=item_type != "once",
        days_of_week=days_str,
    )

    _clear_add_state(context)

    return await show_items_list(
        update,
        context,
        message_id,
        location=location,
        category=category,
        page=999999,
        notice="Задача добавлена.",
    )


async def back_from_add_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
) -> int:
    context.user_data.pop("await_text", None)

    flow = context.user_data.get("add_flow") or {}
    category = flow.get("category")

    if category == "weekly":
        return await ask_days(update, context, message_id)

    if category == "once":
        return await ask_date(update, context, message_id)

    if flow.get("location") and flow.get("category"):
        return await show_items_list(
            update,
            context,
            message_id,
            location=flow.get("location"),
            category=flow.get("category"),
            page=context.user_data.get("edit_page", 1),
            notice="Отменено.",
        )

    return await show_edit_locations(update, context, message_id, notice="Отменено.")


async def cancel_action(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
) -> int:
    item_id = context.user_data.get("edit_item_id")
    flow = context.user_data.get("add_flow") or {}

    _clear_add_state(context)
    _clear_edit_state(context)

    if item_id:
        return await show_item_detail(
            update,
            context,
            item_id,
            message_id,
            notice="Отменено.",
        )

    if flow.get("location") and flow.get("category"):
        return await show_items_list(
            update,
            context,
            message_id,
            location=flow.get("location"),
            category=flow.get("category"),
            page=context.user_data.get("edit_page", 1),
            notice="Отменено.",
        )

    return await show_edit_locations(update, context, message_id, notice="Отменено.")


# =========================================================
# EDIT TEXT
# =========================================================

async def prompt_edit_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    item_id: int,
    message_id=None,
) -> int:
    item = get_item(item_id)

    if not item:
        return await show_items_list(
            update,
            context,
            message_id,
            notice="Пункт не найден.",
        )

    context.user_data["last_item_id"] = item_id

    breadcrumb = get_breadcrumb(item.get("location"), item.get("category"))

    text = (
        f"{breadcrumb}\n\n"
        "Редактирование текста\n\n"
        f"Текущий текст:\n{item.get('text')}\n\n"
        "Отправьте новый текст обычным сообщением."
    )

    kb = text_prompt_keyboard(CB_CANCEL_EDIT)

    new_message_id = await render(
        update,
        context,
        text,
        kb,
        message_id,
    )

    context.user_data["await_text"] = {
        "kind": "edit",
        "item_id": item_id,
        "state": ADMIN_AWAIT_EDIT_TEXT,
        "message_id": new_message_id,
    }

    return _state(context, ADMIN_AWAIT_EDIT_TEXT)


async def cancel_edit_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
) -> int:
    meta = context.user_data.pop("await_text", None) or {}
    item_id = meta.get("item_id") or context.user_data.get("last_item_id")

    if item_id:
        return await show_item_detail(
            update,
            context,
            item_id,
            message_id,
            notice="Отменено.",
        )

    return await show_items_list(update, context, message_id, notice="Отменено.")


async def edit_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    meta = context.user_data.get("await_text")

    if not meta:
        return await show_edit_locations(
            update,
            context,
            None,
            notice="Начните заново.",
        )

    text = (update.message.text or "").strip() if update.message else ""
    message_id = meta.get("message_id")
    state = meta.get("state", ADMIN_AWAIT_NEW_TEXT)

    if not text:
        kb = _text_keyboard_for_meta(meta)

        new_message_id = await render(
            update,
            context,
            "Текст не может быть пустым.\n\nПопробуйте ещё раз.",
            kb,
            message_id,
        )

        if new_message_id:
            meta["message_id"] = new_message_id

        return _state(context, state)

    if len(text) > TEXT_LIMIT:
        kb = _text_keyboard_for_meta(meta)

        new_message_id = await render(
            update,
            context,
            f"Слишком длинно. Максимум {TEXT_LIMIT} символов.\n\nОтправьте текст ещё раз.",
            kb,
            message_id,
        )

        if new_message_id:
            meta["message_id"] = new_message_id

        return _state(context, state)

    if meta.get("kind") == "new":
        context.user_data["add_text"] = text
        return await ask_photo_flag(update, context, message_id)

    if meta.get("kind") == "edit":
        item_id = meta.get("item_id")

        if not item_id:
            return await show_items_list(update, context, message_id)

        update_item_text(item_id, text)
        context.user_data.pop("await_text", None)

        return await show_item_detail(
            update,
            context,
            item_id,
            message_id,
            notice="Сохранено.",
        )

    return _state(context, state)


# =========================================================
# EDIT ITEM CARD ACTIONS
# =========================================================

async def toggle_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    item_id: int,
    message_id: int,
) -> int:
    item = get_item(item_id)

    if not item:
        return await show_items_list(
            update,
            context,
            message_id,
            notice="Пункт не найден.",
        )

    new_value = not bool(item.get("requires_photo"))

    update_item_flags(item_id, requires_photo=new_value)

    return await show_item_detail(
        update,
        context,
        item_id,
        message_id,
        notice=f"Фото: {'включено' if new_value else 'выключено'}",
    )


async def toggle_notification(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    item_id: int,
    message_id: int,
) -> int:
    item = get_item(item_id)

    if not item:
        return await show_items_list(
            update,
            context,
            message_id,
            notice="Пункт не найден.",
        )

    new_value = not bool(item.get("requires_notification"))

    if not new_value:
        update_item_flags(item_id, requires_notification=False)

        return await show_item_detail(
            update,
            context,
            item_id,
            message_id,
            notice="Уведомление выключено.",
        )

    if item.get("notification_time"):
        update_item_flags(item_id, requires_notification=True)

        return await show_item_detail(
            update,
            context,
            item_id,
            message_id,
            notice="Уведомление включено.",
        )

    context.user_data["edit_item_id"] = item_id
    context.user_data.pop("edit_hour", None)

    breadcrumb = get_breadcrumb(item.get("location"), item.get("category"))
    text = f"{breadcrumb}\n\nВыберите время уведомления."

    return await _show_hour_picker(update, context, message_id, text)


async def change_time(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    item_id: int,
    message_id: int,
) -> int:
    item = get_item(item_id)

    if not item:
        return await show_items_list(
            update,
            context,
            message_id,
            notice="Пункт не найден.",
        )

    context.user_data["edit_item_id"] = item_id
    context.user_data.pop("edit_hour", None)

    breadcrumb = get_breadcrumb(item.get("location"), item.get("category"))
    text = f"{breadcrumb}\n\nВыберите время уведомления."

    return await _show_hour_picker(update, context, message_id, text)


async def change_date(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    item_id: int,
    message_id: int,
) -> int:
    item = get_item(item_id)

    if not item or item.get("type") != "once":
        return await show_items_list(
            update,
            context,
            message_id,
            notice="Пункт не найден или не является одноразовым.",
        )

    context.user_data["edit_item_id"] = item_id
    context.user_data["edit_date_mode"] = True

    due_date = item.get("due_date")

    if due_date:
        try:
            dt = datetime.strptime(due_date, "%Y-%m-%d")
            context.user_data["calendar_year"] = dt.year
            context.user_data["calendar_month"] = dt.month
        except ValueError:
            now = datetime.now()
            context.user_data["calendar_year"] = now.year
            context.user_data["calendar_month"] = now.month
    else:
        now = datetime.now()
        context.user_data["calendar_year"] = now.year
        context.user_data["calendar_month"] = now.month

    return await _render_edit_calendar(update, context, message_id)


async def edit_days(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    item_id: int,
    message_id: int,
) -> int:
    item = get_item(item_id)

    if not item or item.get("type") != "weekly":
        return await show_items_list(
            update,
            context,
            message_id,
            notice="Пункт не найден или не является недельным.",
        )

    selected = set(get_week_days(item))

    context.user_data["edit_item_id"] = item_id
    context.user_data["edit_days_selected"] = selected

    return await _render_edit_days(update, context, message_id, item, selected)


async def confirm_delete(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    item_id: int,
    message_id=None,
) -> int:
    item = get_item(item_id)

    if not item:
        return await show_items_list(
            update,
            context,
            message_id,
            notice="Пункт уже удалён.",
        )

    location = item.get("location")
    category = item.get("category")
    page = context.user_data.get("edit_page", 1)

    remove_item(item_id)

    return await show_items_list(
        update,
        context,
        message_id,
        location=location,
        category=category,
        page=page,
        notice="Пункт удалён.",
    )


# =========================================================
# MAIN CALLBACK ROUTER
# =========================================================

async def edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None

    if data == "noop":
        await query.answer()
        return _current_state(context)

    # Отдельно обрабатываем сохранение дней, чтобы показать alert при пустом выборе
    if data == CB_DAYS_SAVE:
        return await days_selection(update, context)

    await query.answer()

    if ":" in data:
        prefix, value = data.split(":", 1)
    else:
        prefix, value = data, None

    # =====================================================
    # HOME / NAV
    # =====================================================

    if data == CB_HOME:
        _clear_all_editor(context)

        try:
            from ..menu.handlers import show_main
            return await show_main(update, context, message_id)
        except Exception:
            return await show_edit_locations(update, context, message_id)

    if data == CB_TO_EDIT:
        _clear_add_state(context)
        _clear_edit_state(context)
        return await show_edit_locations(update, context, message_id)

    if data == CB_TO_CATEGORIES:
        _clear_add_state(context)
        _clear_edit_state(context)
        return await show_edit_categories(update, context, message_id)

    if data == CB_TO_ITEMS:
        _clear_add_state(context)
        _clear_edit_state(context)
        return await show_items_list(update, context, message_id)

    # =====================================================
    # ADD ENTRY
    # =====================================================

    if data == CB_ADD:
        _clear_edit_state(context)
        return await start_add(update, context, message_id)

    if data == CB_ADD_PICK:
        _clear_edit_state(context)
        context.user_data.pop("edit_category", None)
        context.user_data["add_in_progress"] = True
        return await start_add(update, context, message_id)

    # =====================================================
    # LOCATION / CATEGORY / PAGE / ITEM
    # =====================================================

    if prefix == CB_LOC_PREFIX:
        _clear_edit_state(context)

        location = value

        if location not in LOCATIONS:
            return await show_edit_locations(update, context, message_id)

        notice = None

        if context.user_data.get("add_in_progress"):
            notice = "Новая задача\n\nТеперь выберите раздел."

        return await show_edit_categories(
            update,
            context,
            message_id,
            location=location,
            notice=notice,
        )

    if prefix == CB_CAT_PREFIX:
        _clear_edit_state(context)

        try:
            loc, cat = value.split(":", 1)
        except Exception:
            return await show_edit_locations(update, context, message_id)

        if loc not in LOCATIONS or cat not in CATEGORY_LABELS:
            return await show_edit_locations(update, context, message_id)

        context.user_data["edit_location"] = loc
        context.user_data["edit_category"] = cat
        context.user_data["edit_page"] = 1

        if context.user_data.get("add_in_progress"):
            context.user_data.pop("add_in_progress", None)
            return await start_add(update, context, message_id)

        _clear_add_state(context)

        return await show_items_list(
            update,
            context,
            message_id,
            location=loc,
            category=cat,
            page=1,
        )

    if prefix == CB_PAGE_PREFIX:
        _clear_add_state(context)
        _clear_edit_state(context)

        try:
            loc, cat, page_s = value.split(":", 2)
            return await show_items_list(
                update,
                context,
                message_id,
                location=loc,
                category=cat,
                page=int(page_s),
            )
        except Exception:
            return await show_edit_locations(update, context, message_id)

    if prefix == CB_ITEM_PREFIX:
        _clear_add_state(context)
        _clear_edit_state(context)

        try:
            return await show_item_detail(update, context, int(value), message_id)
        except Exception:
            return await show_items_list(update, context, message_id)

    # =====================================================
    # DAYS
    # =====================================================

    if (
        prefix == CB_DAY_TOGGLE_PREFIX
        or prefix == CB_DAY_PRESET_PREFIX
        or data == CB_DAYS_CANCEL
    ):
        return await days_selection(update, context)

    # =====================================================
    # DATE
    # =====================================================

    if data in (CB_MONTH_PREV, CB_MONTH_NEXT) or prefix == CB_DATE_PREFIX:
        return await date_selection(update, context)

    # =====================================================
    # FLAGS
    # =====================================================

    if prefix == CB_PHOTO_FLAG_PREFIX:
        return await photo_flag_selection(update, context)

    if prefix == CB_NOTIF_FLAG_PREFIX:
        return await notification_flag_selection(update, context)

    # =====================================================
    # TIME
    # =====================================================

    if prefix == CB_HOUR_PREFIX:
        return await hour_selection(update, context)

    if prefix == CB_MINUTE_PREFIX:
        return await minute_selection(update, context)

    # =====================================================
    # ITEM CARD EDIT
    # =====================================================

    if prefix == CB_EDIT_ITEM_PREFIX:
        try:
            return await prompt_edit_text(update, context, int(value), message_id)
        except Exception:
            return await show_items_list(update, context, message_id)

    if prefix == CB_DELETE_ITEM_PREFIX:
        try:
            return await show_delete_confirm(update, context, int(value), message_id)
        except Exception:
            return await show_items_list(update, context, message_id)

    if prefix == CB_CONFIRM_DELETE_PREFIX:
        try:
            return await confirm_delete(update, context, int(value), message_id)
        except Exception:
            return await show_items_list(update, context, message_id)

    if prefix == CB_TOGGLE_PHOTO:
        try:
            return await toggle_photo(update, context, int(value), message_id)
        except Exception:
            return await show_items_list(update, context, message_id)

    if prefix == CB_TOGGLE_NOTIFICATION:
        try:
            return await toggle_notification(update, context, int(value), message_id)
        except Exception:
            return await show_items_list(update, context, message_id)

    if prefix == CB_CHANGE_TIME:
        try:
            return await change_time(update, context, int(value), message_id)
        except Exception:
            return await show_items_list(update, context, message_id)

    if prefix == CB_CHANGE_DATE:
        try:
            return await change_date(update, context, int(value), message_id)
        except Exception:
            return await show_items_list(update, context, message_id)

    if prefix == CB_ADD_DAY_PREFIX:
        try:
            return await edit_days(update, context, int(value), message_id)
        except Exception:
            return await show_items_list(update, context, message_id)

    # =====================================================
    # CANCEL / BACK
    # =====================================================

    if data == CB_CANCEL:
        return await cancel_action(update, context, message_id)

    if data == CB_CANCEL_EDIT:
        return await cancel_edit_text(update, context, message_id)

    if data == CB_ADD_BACK_TEXT:
        return await back_from_add_text(update, context, message_id)

    # =====================================================
    # FALLBACK
    # =====================================================

    return await show_edit_locations(update, context, message_id, notice="Начните заново.")