from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from utils.time_utils import now_msk
from .constants import (
    ADMIN_CALENDAR, ADMIN_DAY_REPORT, CB_HOME, CB_TO_CALENDAR,
    MONTHS, LOCATIONS, CATEGORY_LABELS   # добавлены LOCATIONS и CATEGORY_LABELS
)
from .keyboards import calendar_keyboard, day_report_keyboard
from .utils import (
    get_shift_days_for_month, get_day_report,
    full_name, progress_bar, percent, format_date_ru, render
)


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
    report = get_day_report(date_str)

    lines = [f"📊 Отчёт за {format_date_ru(date_str)}", ""]

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
        else:
            lines.append("Чек-лист пуст")

        lines.append("")

    text = "\n".join(lines).strip()
    if notice:
        text = f"{notice}\n\n{text}"

    await render(update, context, text, day_report_keyboard(), message_id)
    return ADMIN_DAY_REPORT


async def calendar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    message_id = query.message.message_id if query.message else None

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
            return await show_day_report(update, context, date_str, message_id)
        except Exception:
            return await show_calendar(update, context, message_id)

    return await show_calendar(update, context, message_id)