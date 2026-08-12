from datetime import datetime
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ContextTypes
from utils.time_utils import now_msk
from .constants import (
    ADMIN_CALENDAR, ADMIN_DAY_REPORT, CB_HOME, CB_TO_CALENDAR,
    CB_PREV_MONTH, CB_NEXT_MONTH, CB_DAY_PREFIX,
    MONTHS, LOCATIONS, CATEGORY_LABELS
)
from .keyboards import calendar_keyboard, day_report_keyboard
from .utils import (
    get_shift_days_for_month, get_day_report,
    full_name, progress_bar, percent, format_date_ru, render
)
import logging

logger = logging.getLogger(__name__)


async def show_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id=None, notice=None) -> int:
    now = now_msk()
    year = context.user_data.get("calendar_year", now.year)
    month = context.user_data.get("calendar_month", now.month)
    context.user_data["calendar_year"] = year
    context.user_data["calendar_month"] = month

    shift_days = get_shift_days_for_month(year, month)
    text = f"📅 {MONTHS[month - 1]} {year}\n\n✅ — день со сменами\nНажмите на день для отчёта."
    if notice:
        text = f"{notice}\n\n{text}"

    await render(update, context, text, calendar_keyboard(year, month, shift_days), message_id)
    return ADMIN_CALENDAR


async def show_day_report(update: Update, context: ContextTypes.DEFAULT_TYPE, date_str: str,
                          message_id=None, notice=None) -> int:
    logger.info(f"📊 Запрос отчёта за {date_str}")
    report = get_day_report(date_str)
    context.user_data["report_date"] = date_str

    lines = [f"📊 Отчёт за {format_date_ru(date_str)}", ""]

    has_bar_media = False
    has_kitchen_media = False

    for loc_key, loc_label in LOCATIONS.items():
        loc_data = report[loc_key]
        shifts = loc_data["shifts"]
        items = loc_data["items"]
        done = loc_data["done"]
        total = loc_data["total"]
        grouped = loc_data["grouped"]

        if shifts:
            names = [full_name(s) for s in shifts]
            lines.append(f"{loc_label} · {len(shifts)} чел.: {', '.join(names)}")
        else:
            lines.append(f"{loc_label} · смен нет")

        if total > 0:
            bar = progress_bar(done, total)
            pct = percent(done, total)
            lines.append(f"Прогресс: {bar} {done}/{total} · {pct}%")
            for cat, cat_items in grouped.items():
                cat_label = CATEGORY_LABELS.get(cat, cat)
                cat_done = sum(1 for i in cat_items if i.get("completed"))
                lines.append(f"  {cat_label}: {cat_done}/{len(cat_items)}")
                for item in cat_items:
                    if item.get("media_count", 0) > 0:
                        if loc_key == "bar":
                            has_bar_media = True
                        else:
                            has_kitchen_media = True
                        text_preview = item.get("text", "")[:35]
                        if len(item.get("text", "")) > 35:
                            text_preview += "…"
                        lines.append(f"    • {text_preview} 📸{item['media_count']}")
        else:
            lines.append("Чек-лист пуст")

        lines.append("")

    text = "\n".join(lines).strip()
    if notice:
        text = f"{notice}\n\n{text}"

    logger.info(f"🟢 has_bar_media={has_bar_media}, has_kitchen_media={has_kitchen_media}")
    kb = day_report_keyboard(has_bar_media, has_kitchen_media)
    await render(update, context, text, kb, message_id)
    return ADMIN_DAY_REPORT


async def show_location_media(update: Update, context: ContextTypes.DEFAULT_TYPE, location: str, date_str: str, message_id=None) -> int:
    logger.info(f"👁 Админ запросил вложения для локации {location} за {date_str}")
    report = get_day_report(date_str)
    loc_data = report.get(location)
    if not loc_data:
        logger.warning(f"⚠️ Нет данных по локации {location}")
        await render(update, context, "Нет данных по этой локации.", None, message_id)
        return ADMIN_DAY_REPORT

    all_media = []
    for item in loc_data.get("items", []):
        media = item.get("media_items", [])
        if media:
            logger.info(f"📦 Задача {item.get('id')} имеет {len(media)} вложений")
            all_media.extend(media)

    if not all_media:
        logger.warning(f"⚠️ Нет вложений для локации {location}")
        await render(update, context, "Нет вложений.", None, message_id)
        return ADMIN_DAY_REPORT

    logger.info(f"📦 Всего вложений для отображения: {len(all_media)}")

    if len(all_media) > 10:
        all_media = all_media[:10]
        logger.info("✂️ Обрезано до 10 вложений")

    media_group = []
    for i, media in enumerate(all_media):
        if media.get("type") == "photo":
            media_obj = InputMediaPhoto(media=media["file_id"])
        elif media.get("type") == "video":
            media_obj = InputMediaVideo(media=media["file_id"])
        else:
            continue
        if i == 0:
            media_obj.caption = f"📸 Вложения по {LOCATIONS.get(location, location)} за {format_date_ru(date_str)}"
        media_group.append(media_obj)

    if media_group:
        try:
            await context.bot.send_media_group(chat_id=update.effective_chat.id, media=media_group)
            logger.info(f"✅ Вложения отправлены админу")
            notice = "Вложения отправлены выше."
        except Exception as e:
            logger.error(f"❌ Ошибка отправки вложений админу: {e}")
            notice = "Не удалось отправить вложения."
    else:
        notice = "Нет подходящих медиа."

    return await show_day_report(update, context, date_str, message_id, notice=notice)


async def calendar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data
    message_id = query.message.message_id if query.message else None

    logger.info(f"🔄 Получен callback: {data}")

    if data == "noop":
        await query.answer()
        return _current_state(context)

    await query.answer()

    if data == CB_HOME:
        from ..menu.handlers import show_main
        return await show_main(update, context, message_id)

    if data == CB_TO_CALENDAR:
        return await show_calendar(update, context, message_id)

    if data == CB_PREV_MONTH:
        year = context.user_data.get("calendar_year", now_msk().year)
        month = context.user_data.get("calendar_month", now_msk().month)
        if month == 1:
            month, year = 12, year - 1
        else:
            month -= 1
        context.user_data["calendar_year"] = year
        context.user_data["calendar_month"] = month
        return await show_calendar(update, context, message_id)

    if data == CB_NEXT_MONTH:
        year = context.user_data.get("calendar_year", now_msk().year)
        month = context.user_data.get("calendar_month", now_msk().month)
        if month == 12:
            month, year = 1, year + 1
        else:
            month += 1
        context.user_data["calendar_year"] = year
        context.user_data["calendar_month"] = month
        return await show_calendar(update, context, message_id)

    if data.startswith(CB_DAY_PREFIX + ":"):
        try:
            date_str = data.split(":", 1)[1]
            date_str = datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")
            logger.info(f"📅 Выбран день: {date_str}")
            return await show_day_report(update, context, date_str, message_id)
        except Exception as e:
            logger.error(f"❌ Ошибка разбора даты: {e}")
            return await show_calendar(update, context, message_id)

    if data.startswith("show_media:"):
        location = data.split(":", 1)[1]
        date_str = context.user_data.get("report_date")
        if not date_str:
            logger.warning("⚠️ Дата не найдена для показа вложений")
            return await show_calendar(update, context, message_id, notice="Дата не найдена.")
        return await show_location_media(update, context, location, date_str, message_id)

    return await show_calendar(update, context, message_id)