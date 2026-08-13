import logging
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
    CB_HOME,
    CB_TO_CALENDAR,
    CB_PREV_MONTH,
    CB_NEXT_MONTH,
    CB_DAY_PREFIX,
    CB_NOOP,
    CB_REPORT_SHORT,
    CB_REPORT_FULL,
    CB_REPORT_PHOTOS_ON,
    CB_REPORT_PHOTOS_OFF,
    CB_SHOW_MEDIA_PREFIX,
    REPORT_MODE_SHORT,
    REPORT_MODE_FULL,
    MONTHS,
    LOCATIONS,
    MEDIA_CHUNK_SIZE,
    MEDIA_SEND_LIMIT,
)

from .keyboards import (
    calendar_keyboard,
    day_report_keyboard,
)

from .utils import (
    get_shift_days_for_month,
    get_day_report,
    get_report_text,
    format_date_ru,
    render,
)

logger = logging.getLogger(__name__)


# =========================================================
# HELPERS
# =========================================================

def _state(context: ContextTypes.DEFAULT_TYPE, state: int) -> int:
    context.user_data["ui_state"] = state
    return state


def _current_state(context: ContextTypes.DEFAULT_TYPE) -> int:
    return context.user_data.get("ui_state", ADMIN_CALENDAR)


def _get_mode(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("report_mode", REPORT_MODE_SHORT)


def _get_show_photos(context: ContextTypes.DEFAULT_TYPE) -> bool:
    return bool(context.user_data.get("report_photos", True))


def _set_calendar_to_date(context: ContextTypes.DEFAULT_TYPE, date_str: str) -> None:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        context.user_data["calendar_year"] = dt.year
        context.user_data["calendar_month"] = dt.month
    except Exception:
        pass


# =========================================================
# SCREENS
# =========================================================

async def show_calendar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id=None,
    notice=None,
) -> int:
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
        "✅ — день со сменами\n"
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
) -> int:
    mode = _get_mode(context)
    show_photos = _get_show_photos(context)

    context.user_data["report_date"] = date_str
    _set_calendar_to_date(context, date_str)

    try:
        text, has_bar_media, has_kitchen_media = get_report_text(
            date_str,
            mode,
            show_photos,
        )
    except Exception as e:
        logger.error("Ошибка построения отчёта: %s", e)
        text = "Не удалось загрузить отчёт."
        has_bar_media = False
        has_kitchen_media = False

    if notice:
        text = f"{notice}\n\n{text}"

    await render(
        update,
        context,
        text,
        day_report_keyboard(
            mode=mode,
            show_photos=show_photos,
            has_bar_media=has_bar_media,
            has_kitchen_media=has_kitchen_media,
        ),
        message_id,
    )

    return _state(context, ADMIN_DAY_REPORT)


async def show_location_media(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    location: str,
    date_str: str,
    message_id=None,
) -> int:
    chat_id = update.effective_chat.id if update.effective_chat else None

    if not chat_id:
        return await show_day_report(
            update,
            context,
            date_str,
            message_id,
            notice="Не удалось отправить вложения.",
        )

    if location not in LOCATIONS:
        return await show_day_report(
            update,
            context,
            date_str,
            message_id,
            notice="Неизвестная локация.",
        )

    report = get_day_report(date_str)
    loc_data = report.get(location)

    if not loc_data:
        return await show_day_report(
            update,
            context,
            date_str,
            message_id,
            notice="Нет данных по этой локации.",
        )

    media = []

    for item in loc_data.get("items", []):
        item_media = item.get("media_items", [])
        if item_media:
            media.extend(item_media)

    if not media:
        return await show_day_report(
            update,
            context,
            date_str,
            message_id,
            notice="Нет вложений.",
        )

    total_media = len(media)

    if total_media > MEDIA_SEND_LIMIT:
        media_to_send = media[:MEDIA_SEND_LIMIT]
        notice = f"Отправлены первые {MEDIA_SEND_LIMIT} из {total_media}."
    else:
        media_to_send = media
        notice = "Вложения отправлены выше."

    try:
        for start in range(0, len(media_to_send), MEDIA_CHUNK_SIZE):
            chunk = media_to_send[start:start + MEDIA_CHUNK_SIZE]
            media_group = []

            for index, media_item in enumerate(chunk):
                file_id = media_item.get("file_id")

                if not file_id:
                    continue

                caption = (
                    f"📸 {LOCATIONS.get(location, location)} · {format_date_ru(date_str)}"
                    if start == 0 and index == 0
                    else None
                )

                if media_item.get("type") == "video":
                    media_group.append(
                        InputMediaVideo(
                            media=file_id,
                            caption=caption,
                        )
                    )
                else:
                    media_group.append(
                        InputMediaPhoto(
                            media=file_id,
                            caption=caption,
                        )
                    )

            if media_group:
                await context.bot.send_media_group(
                    chat_id=chat_id,
                    media=media_group,
                )

    except Exception as e:
        logger.error("Ошибка отправки вложений: %s", e)
        notice = "Не удалось отправить вложения."

    return await show_day_report(
        update,
        context,
        date_str,
        message_id,
        notice=notice,
    )


# =========================================================
# CALLBACK ROUTER
# =========================================================

async def calendar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    if not query:
        return _current_state(context)

    data = query.data or ""
    message_id = query.message.message_id if query.message else None

    if data == CB_NOOP:
        await query.answer()
        return _current_state(context)

    await query.answer()

    # Домой
    if data == CB_HOME:
        try:
            from ..menu.handlers import show_main
            return await show_main(update, context, message_id)
        except Exception:
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
    if data.startswith(f"{CB_DAY_PREFIX}:"):
        raw_date = data.split(":", 1)[1]

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

    # Режим отчёта
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

    # Фото вкл/выкл
    if data == CB_REPORT_PHOTOS_ON:
        context.user_data["report_photos"] = True
        date_str = context.user_data.get("report_date")

        if not date_str:
            return await show_calendar(update, context, message_id)

        return await show_day_report(update, context, date_str, message_id)

    if data == CB_REPORT_PHOTOS_OFF:
        context.user_data["report_photos"] = False
        date_str = context.user_data.get("report_date")

        if not date_str:
            return await show_calendar(update, context, message_id)

        return await show_day_report(update, context, date_str, message_id)

    # Отправка медиа по локации
    if data.startswith(f"{CB_SHOW_MEDIA_PREFIX}:"):
        location = data.split(":", 1)[1]
        date_str = context.user_data.get("report_date")

        if not date_str:
            return await show_calendar(
                update,
                context,
                message_id,
                notice="Сначала выберите день.",
            )

        return await show_location_media(
            update,
            context,
            location,
            date_str,
            message_id,
        )

    # Fallback
    if (
        context.user_data.get("ui_state") == ADMIN_DAY_REPORT
        and context.user_data.get("report_date")
    ):
        return await show_day_report(
            update,
            context,
            context.user_data.get("report_date"),
            message_id,
        )

    return await show_calendar(update, context, message_id)