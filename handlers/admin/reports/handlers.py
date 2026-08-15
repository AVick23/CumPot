import logging
import asyncio
from datetime import datetime
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes

try:
    from utils.time_utils import now_msk
except Exception:
    def now_msk():
        return datetime.now()

from .constants import (
    ADMIN_CALENDAR,
    ADMIN_DAY_REPORT,
    ADMIN_PHOTO_OVERVIEW,
    ADMIN_PHOTO_LOCATION,
    ADMIN_PHOTO_CATEGORY,
    CB_HOME,
    CB_TO_CALENDAR,
    CB_PREV_MONTH,
    CB_NEXT_MONTH,
    CB_DAY_PREFIX,
    CB_NOOP,
    CB_REPORT_SHORT,
    CB_REPORT_FULL,
    CB_PHOTO_REPORT,
    CB_SHOW_MEDIA_PREFIX,
    CB_PHOTO_LOC_PREFIX,
    CB_PHOTO_CAT_PREFIX,
    CB_PHOTO_ALL_LOC,
    CB_PHOTO_ALL_CAT,
    CB_PHOTO_TASK_PREFIX,
    CB_PHOTO_PAGE_PREFIX,
    CB_PHOTO_BACK_DAY,
    CB_PHOTO_BACK_OVERVIEW,
    CB_PHOTO_BACK_LOC,
    CB_TAB_CHECKLIST,
    CB_TAB_SHIFT_REPORTS,
    REPORT_MODE_SHORT,
    REPORT_MODE_FULL,
    MONTHS,
    LOCATIONS,
    CATEGORY_LABELS,
    MEDIA_CHUNK_SIZE,
    TASK_SEND_DELAY,
)
from .keyboards import (
    calendar_keyboard,
    day_report_keyboard,
    photo_overview_keyboard,
    photo_location_keyboard,
    photo_category_keyboard,
)
from .utils import (
    get_shift_days_for_month,
    get_day_report,
    get_report_text,
    format_date_ru,
    render,
    paginate_list,
    get_photo_overview,
    get_location_photo_menu,
    get_category_photo_tasks,
    get_task_by_id_from_report,
    build_task_media_caption,
    get_shift_reports_for_date,
    format_shift_report_text,
)

logger = logging.getLogger(__name__)


# ==========================================================
# HELPERS
# ==========================================================

def _state(context, state):
    context.user_data["ui_state"] = state
    return state


def _current_state(context):
    return context.user_data.get("ui_state", ADMIN_CALENDAR)


def _get_mode(context):
    return context.user_data.get("report_mode", REPORT_MODE_SHORT)


def _get_tab(context):
    return context.user_data.get("report_tab", CB_TAB_CHECKLIST)


def _set_tab(context, tab):
    context.user_data["report_tab"] = tab


def _set_calendar_to_date(context, date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        context.user_data["calendar_year"] = dt.year
        context.user_data["calendar_month"] = dt.month
    except Exception:
        pass


# ==========================================================
# BASE SCREENS
# ==========================================================

async def show_calendar(
    update,
    context,
    message_id=None,
    notice=None,
):
    now = now_msk()
    year = context.user_data.get("calendar_year", now.year)
    month = context.user_data.get("calendar_month", now.month)

    if not (1 <= month <= 12):
        month = now.month

    context.user_data["calendar_year"] = year
    context.user_data["calendar_month"] = month

    shift_days = get_shift_days_for_month(year, month)
    selected_date = context.user_data.get("report_date")
    today = now.strftime("%Y-%m-%d")

    text = (
        f"Отчёты\n\n"
        f"{MONTHS[month - 1]} {year}\n\n"
        "✓ — день со сменами\n"
        "Выберите день."
    )
    if notice:
        text = f"{notice}\n\n{text}"

    await render(
        update,
        context,
        text,
        calendar_keyboard(
            year,
            month,
            shift_days,
            selected_date=selected_date,
            today=today,
        ),
        message_id,
    )
    return _state(context, ADMIN_CALENDAR)


async def show_day_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    date_str: str,
    message_id=None,
    notice=None,
    tab: str = None,
) -> int:
    if tab:
        _set_tab(context, tab)

    current_tab = _get_tab(context)
    mode = _get_mode(context)
    context.user_data["report_date"] = date_str
    _set_calendar_to_date(context, date_str)

    has_bar_media = False
    has_kitchen_media = False
    parse_mode = None

    # =========================================================
    # ВКЛАДКА: ЧЕК-ЛИСТЫ
    # =========================================================
    if current_tab == CB_TAB_CHECKLIST:
        try:
            text, has_bar_media, has_kitchen_media = get_report_text(date_str, mode)
        except Exception as e:
            logger.error("Ошибка построения отчёта чек-листов: %s", e)
            text = "❌ Не удалось загрузить отчёт по чек-листам."

    # =========================================================
    # ВКЛАДКА: СМЕННЫЕ ОТЧЁТЫ (HTML + Разделители)
    # =========================================================
    elif current_tab == CB_TAB_SHIFT_REPORTS:
        parse_mode = "HTML"
        reports = get_shift_reports_for_date(date_str)
        lines = [
            "<b>📄 СМЕННЫЕ ОТЧЁТЫ</b>",
            f"🗓 <i>{format_date_ru(date_str)}</i>",
            "━━━━━━━━━━━━━━━━━━━━",
        ]

        opening = reports.get("opening")
        lines.append("\n<b>☀️ ОТКРЫТИЕ СМЕНЫ</b>")
        if opening:
            raw_text = format_shift_report_text(opening)
            safe_text = (
                raw_text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            lines.append(safe_text)
        else:
            lines.append("<i>⚠️ Отчёт ещё не сохранён</i>")

        lines.append("\n━━━━━━━━━━━━━━━━━━━━")

        closing = reports.get("closing")
        lines.append("\n<b>🌙 ЗАКРЫТИЕ СМЕНЫ</b>")
        if closing:
            raw_text = format_shift_report_text(closing)
            safe_text = (
                raw_text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            lines.append(safe_text)
        else:
            lines.append("<i>⚠️ Отчёт ещё не сохранён</i>")

        text = "\n".join(lines)

    if notice:
        if parse_mode == "HTML":
            text = f"<b>ℹ️ {notice}</b>\n\n{text}"
        else:
            text = f"{notice}\n\n{text}"

    kb = day_report_keyboard(
        mode=mode,
        has_bar_media=has_bar_media,
        has_kitchen_media=has_kitchen_media,
        current_tab=current_tab,
    )

    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id and message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=kb,
                parse_mode=parse_mode,
            )
        except Exception as e:
            logger.warning("Edit failed in show_day_report: %s", e)
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=kb,
                parse_mode=parse_mode,
            )
    elif chat_id:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=kb,
            parse_mode=parse_mode,
        )

    return _state(context, ADMIN_DAY_REPORT)


# ==========================================================
# PHOTO REPORT FOR CHECKLISTS
# ==========================================================

async def show_photo_overview(
    update,
    context,
    message_id=None,
    notice=None,
):
    date_str = context.user_data.get("report_date")
    if not date_str:
        return await show_calendar(
            update,
            context,
            message_id,
            notice="Сначала выберите день.",
        )

    overview = get_photo_overview(date_str)
    if overview.get("total", 0) <= 0:
        return await show_day_report(
            update,
            context,
            date_str,
            message_id,
            notice="За этот день нет вложений.",
        )

    context.user_data.pop("photo_location", None)
    context.user_data.pop("photo_category", None)
    context.user_data.pop("photo_page", None)

    text = (
        f"Фотоотчёт\n"
        f"{format_date_ru(date_str)}\n\n"
        f"Вложений · {overview.get('total', 0)}\n\n"
        "Выберите локацию."
    )
    if notice:
        text = f"{notice}\n\n{text}"

    await render(
        update,
        context,
        text,
        photo_overview_keyboard(
            bar_media_count=overview.get("bar", 0),
            kitchen_media_count=overview.get("kitchen", 0),
        ),
        message_id,
    )
    return _state(context, ADMIN_PHOTO_OVERVIEW)


async def show_photo_location_menu(
    update,
    context,
    location,
    message_id=None,
    notice=None,
):
    date_str = context.user_data.get("report_date")
    if not date_str:
        return await show_calendar(
            update,
            context,
            message_id,
            notice="Сначала выберите день.",
        )

    if location not in LOCATIONS:
        return await show_photo_overview(update, context, message_id)

    menu = get_location_photo_menu(date_str, location)
    if menu.get("total_media", 0) <= 0:
        return await show_photo_overview(
            update,
            context,
            message_id,
            notice="В этой локации нет вложений.",
        )

    context.user_data["photo_location"] = location
    context.user_data.pop("photo_category", None)
    context.user_data.pop("photo_page", None)

    location_label = LOCATIONS.get(location, location)
    text = (
        f"{location_label}\n"
        f"{format_date_ru(date_str)}\n\n"
        f"Вложений · {menu.get('total_media', 0)}\n"
        f"Задач · {menu.get('task_count', 0)}\n\n"
        "Выберите категорию или отправьте всё."
    )
    if notice:
        text = f"{notice}\n\n{text}"

    await render(
        update,
        context,
        text,
        photo_location_keyboard(menu),
        message_id,
    )
    return _state(context, ADMIN_PHOTO_LOCATION)


async def show_photo_category_menu(
    update,
    context,
    location,
    category,
    page=1,
    message_id=None,
    notice=None,
):
    date_str = context.user_data.get("report_date")
    if not date_str:
        return await show_calendar(
            update,
            context,
            message_id,
            notice="Сначала выберите день.",
        )

    if location not in LOCATIONS:
        return await show_photo_overview(update, context, message_id)

    data = get_category_photo_tasks(date_str, location, category)
    if data.get("task_count", 0) <= 0:
        return await show_photo_location_menu(
            update,
            context,
            location,
            message_id,
            notice="В этой категории нет вложений.",
        )

    tasks = data.get("tasks", [])
    page_items, total_pages, page = paginate_list(tasks, page)

    context.user_data["photo_location"] = location
    context.user_data["photo_category"] = category
    context.user_data["photo_page"] = page

    location_label = LOCATIONS.get(location, location)
    category_label = CATEGORY_LABELS.get(category, category)
    text = (
        f"{location_label} · {category_label}\n"
        f"{format_date_ru(date_str)}\n\n"
        f"Вложений · {data.get('media_count', 0)}\n"
        f"Задач · {data.get('task_count', 0)}\n\n"
        "Нажмите на задачу, чтобы отправить её фото."
    )
    if notice:
        text = f"{notice}\n\n{text}"

    await render(
        update,
        context,
        text,
        photo_category_keyboard(
            location=location,
            category=category,
            page_items=page_items,
            page=page,
            total_pages=total_pages,
        ),
        message_id,
    )
    return _state(context, ADMIN_PHOTO_CATEGORY)


async def _send_task_media(
    update,
    context,
    item,
    location,
    date_str,
):
    chat_id = update.effective_chat.id if update.effective_chat else None
    if not chat_id:
        return 0

    media_items = item.get("media_items", [])
    if not media_items:
        return 0

    caption = build_task_media_caption(item, location, date_str)
    sent_count = 0

    for start in range(0, len(media_items), MEDIA_CHUNK_SIZE):
        chunk = media_items[start:start + MEDIA_CHUNK_SIZE]
        media_group = []
        for index, media in enumerate(chunk):
            file_id = media.get("file_id")
            if not file_id:
                continue
            media_caption = caption if start == 0 and index == 0 else None
            if media.get("type") == "video":
                media_group.append(
                    InputMediaVideo(
                        media=file_id,
                        caption=media_caption,
                    )
                )
            else:
                media_group.append(
                    InputMediaPhoto(
                        media=file_id,
                        caption=media_caption,
                    )
                )
        if media_group:
            await context.bot.send_media_group(
                chat_id=chat_id,
                media=media_group,
            )
            sent_count += len(media_group)

    return sent_count


async def _send_tasks_media(
    update,
    context,
    tasks,
    location,
    date_str,
):
    task_sent = 0
    media_sent = 0
    success = True

    for item in tasks:
        try:
            sent = await _send_task_media(
                update,
                context,
                item,
                location,
                date_str,
            )
            if sent > 0:
                task_sent += 1
                media_sent += sent
            await asyncio.sleep(TASK_SEND_DELAY)
        except Exception as e:
            logger.error(
                "Ошибка отправки медиа задачи %s: %s",
                item.get("id"),
                e,
                exc_info=True,
            )
            success = False
            break

    return task_sent, media_sent, success


async def send_all_location_photos(
    update,
    context,
    location,
    message_id=None,
):
    date_str = context.user_data.get("report_date")
    if not date_str:
        return await show_calendar(update, context, message_id)

    menu = get_location_photo_menu(date_str, location)
    tasks = menu.get("items", [])
    if not tasks:
        return await show_photo_location_menu(
            update,
            context,
            location,
            message_id,
            notice="Нет вложений для отправки.",
        )

    logger.info(
        "📤 Админ запросил отправку всех фото локации %s за %s",
        location,
        date_str,
    )
    task_count, media_count, success = await _send_tasks_media(
        update,
        context,
        tasks,
        location,
        date_str,
    )

    if success:
        notice = f"Отправлено файлов · {media_count}"
    else:
        notice = f"Отправлено файлов · {media_count}, есть ошибки"

    return await show_photo_location_menu(
        update,
        context,
        location,
        message_id,
        notice=notice,
    )


async def send_all_category_photos(
    update,
    context,
    location,
    category,
    message_id=None,
):
    date_str = context.user_data.get("report_date")
    if not date_str:
        return await show_calendar(update, context, message_id)

    data = get_category_photo_tasks(date_str, location, category)
    tasks = data.get("tasks", [])
    if not tasks:
        return await show_photo_category_menu(
            update,
            context,
            location,
            category,
            1,
            message_id,
            notice="Нет вложений для отправки.",
        )

    logger.info(
        "📤 Админ запросил отправку всех фото категории %s / %s за %s",
        location,
        category,
        date_str,
    )
    task_count, media_count, success = await _send_tasks_media(
        update,
        context,
        tasks,
        location,
        date_str,
    )

    if success:
        notice = f"Отправлено файлов · {media_count}"
    else:
        notice = f"Отправлено файлов · {media_count}, есть ошибки"

    page = context.user_data.get("photo_page", 1)
    return await show_photo_category_menu(
        update,
        context,
        location,
        category,
        page,
        message_id,
        notice=notice,
    )


async def send_task_photos(
    update,
    context,
    item_id,
    message_id=None,
):
    date_str = context.user_data.get("report_date")
    if not date_str:
        return await show_calendar(update, context, message_id)

    item, location = get_task_by_id_from_report(date_str, item_id)
    if not item or not location:
        return await show_photo_overview(
            update,
            context,
            message_id,
            notice="Задача не найдена.",
        )

    logger.info(
        "📤 Админ запросил фото конкретной задачи %s за %s",
        item_id,
        date_str,
    )
    sent = await _send_task_media(
        update,
        context,
        item,
        location,
        date_str,
    )

    if sent <= 0:
        notice = "У этой задачи нет вложений."
    else:
        notice = f"Отправлено файлов · {sent}"

    current_location = context.user_data.get("photo_location")
    current_category = context.user_data.get("photo_category")
    item_category = (item.get("category") or "").strip()

    if current_location == location and current_category == item_category:
        page = context.user_data.get("photo_page", 1)
        return await show_photo_category_menu(
            update,
            context,
            location,
            current_category,
            page,
            message_id,
            notice=notice,
        )

    return await show_photo_location_menu(
        update,
        context,
        location,
        message_id,
        notice=notice,
    )


# ==========================================================
# CALLBACK ROUTER
# ==========================================================

async def calendar_callback(update, context):
    query = update.callback_query
    if not query:
        return _current_state(context)

    data = (query.data or "").strip()
    message_id = getattr(query.message, "message_id", None) if query.message else None

    if data == CB_NOOP:
        await query.answer()
        return _current_state(context)

    send_actions = {
        CB_PHOTO_ALL_LOC,
        CB_PHOTO_ALL_CAT,
    }
    if (
        data in send_actions
        or data.startswith(f"{CB_PHOTO_TASK_PREFIX}:")
    ):
        await query.answer("Отправляю…")
    else:
        await query.answer()

    if ":" in data:
        prefix, value = data.split(":", 1)
        prefix = prefix.strip()
        value = value.strip() if value is not None else None
    else:
        prefix, value = data, None

    # Домой
    if data == CB_HOME:
        try:
            from ..menu.handlers import show_main
            result = await show_main(update, context, message_id)
            if result is not None:
                return result
        except Exception:
            pass
        return await show_calendar(update, context, message_id)

    # Назад к календарю
    if data == CB_TO_CALENDAR:
        return await show_calendar(update, context, message_id)

    # Навигация по месяцам
    if data in (CB_PREV_MONTH, CB_NEXT_MONTH):
        now = now_msk()
        year = context.user_data.get("calendar_year", now.year)
        month = context.user_data.get("calendar_month", now.month)
        if data == CB_PREV_MONTH:
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
        return await show_calendar(update, context, message_id)

    # Выбор дня
    if prefix == CB_DAY_PREFIX:
        raw_date = value or ""
        try:
            if len(raw_date) == 8:
                date_str = datetime.strptime(raw_date, "%Y%m%d").strftime("%Y-%m-%d")
            else:
                date_str = datetime.strptime(raw_date, "%Y-%m-%d").strftime("%Y-%m-%d")
            return await show_day_report(update, context, date_str, message_id)
        except Exception as e:
            logger.error("Ошибка разбора даты: %s", e)
            return await show_calendar(
                update,
                context,
                message_id,
                notice="Не удалось прочитать дату.",
            )

    # Переключение вкладок
    if data in (CB_TAB_CHECKLIST, CB_TAB_SHIFT_REPORTS):
        date_str = context.user_data.get("report_date")
        if not date_str:
            return await show_calendar(update, context, message_id)
        return await show_day_report(
            update,
            context,
            date_str,
            message_id,
            tab=data,
        )

    # Режимы отчёта
    if data == CB_REPORT_SHORT:
        context.user_data["report_mode"] = REPORT_MODE_SHORT
        date_str = context.user_data.get("report_date")
        if not date_str:
            return await show_calendar(update, context, message_id)
        return await show_day_report(update, context, date_str, message_id)

    if data == CB_REPORT_FULL:
        context.user_data["report_mode"] = REPORT_MODE_FULL
        date_str = context.user_data.get("report_date")
        if not date_str:
            return await show_calendar(update, context, message_id)
        return await show_day_report(update, context, date_str, message_id)

    # Фотоотчёт чек-листов
    if data == CB_PHOTO_REPORT:
        return await show_photo_overview(update, context, message_id)

    # Назад: фотоотчёт чек-листов
    if data == CB_PHOTO_BACK_DAY:
        date_str = context.user_data.get("report_date")
        if not date_str:
            return await show_calendar(update, context, message_id)
        return await show_day_report(update, context, date_str, message_id)

    if data == CB_PHOTO_BACK_OVERVIEW:
        return await show_photo_overview(update, context, message_id)

    if data == CB_PHOTO_BACK_LOC:
        location = context.user_data.get("photo_location")
        if location:
            return await show_photo_location_menu(update, context, location, message_id)
        return await show_photo_overview(update, context, message_id)

    # Локация
    if prefix == CB_PHOTO_LOC_PREFIX:
        return await show_photo_location_menu(update, context, value, message_id)

    # Категория
    if prefix == CB_PHOTO_CAT_PREFIX:
        location = context.user_data.get("photo_location")
        if not location:
            return await show_photo_overview(update, context, message_id)
        return await show_photo_category_menu(
            update,
            context,
            location,
            value,
            1,
            message_id,
        )

    # Отправить всю локацию
    if data == CB_PHOTO_ALL_LOC:
        location = context.user_data.get("photo_location")
        if not location:
            return await show_photo_overview(update, context, message_id)
        return await send_all_location_photos(update, context, location, message_id)

    # Отправить всю категорию
    if data == CB_PHOTO_ALL_CAT:
        location = context.user_data.get("photo_location")
        category = context.user_data.get("photo_category")
        if not location or not category:
            return await show_photo_overview(update, context, message_id)
        return await send_all_category_photos(
            update,
            context,
            location,
            category,
            message_id,
        )

    # Отправить конкретную задачу
    if prefix == CB_PHOTO_TASK_PREFIX:
        try:
            item_id = int(value)
        except (TypeError, ValueError):
            return await show_photo_overview(update, context, message_id)
        return await send_task_photos(update, context, item_id, message_id)

    # Пагинация задач
    if prefix == CB_PHOTO_PAGE_PREFIX:
        location = context.user_data.get("photo_location")
        category = context.user_data.get("photo_category")
        if not location or not category:
            return await show_photo_overview(update, context, message_id)
        try:
            page = int(value)
        except (TypeError, ValueError):
            page = 1
        return await show_photo_category_menu(
            update,
            context,
            location,
            category,
            page,
            message_id,
        )

    # Legacy media:bar / media:kitchen
    if prefix == CB_SHOW_MEDIA_PREFIX:
        if value in LOCATIONS:
            return await show_photo_location_menu(update, context, value, message_id)
        return await show_photo_overview(update, context, message_id)

    # Fallback
    state = _current_state(context)
    date_str = context.user_data.get("report_date")
    location = context.user_data.get("photo_location")
    category = context.user_data.get("photo_category")

    if state in (ADMIN_PHOTO_OVERVIEW, ADMIN_PHOTO_LOCATION, ADMIN_PHOTO_CATEGORY) and date_str:
        if state == ADMIN_PHOTO_CATEGORY and location and category:
            return await show_photo_category_menu(
                update,
                context,
                location,
                category,
                context.user_data.get("photo_page", 1),
                message_id,
            )
        if state == ADMIN_PHOTO_LOCATION and location:
            return await show_photo_location_menu(
                update,
                context,
                location,
                message_id,
            )
        return await show_photo_overview(update, context, message_id)

    if state == ADMIN_DAY_REPORT and date_str:
        return await show_day_report(
            update,
            context,
            date_str,
            message_id,
        )

    return await show_calendar(update, context, message_id)