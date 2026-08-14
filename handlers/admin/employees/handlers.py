import logging
from datetime import datetime, timedelta

from telegram import Update, InputMediaPhoto
from telegram.ext import ContextTypes

from db import get_connection
from db.users import get_all_users, get_user
from db.profile import (
    get_employee_full_info,
    update_employee_status,
    update_employee_comment,
    set_salary_rate,
    get_taxi_summary,
    get_salary_history,
)

from utils.time_utils import today_msk_str

from .constants import (
    EMPLOYEES_LIST,
    EMPLOYEE_DETAIL,
    EMPLOYEE_PROFILE,
    EMPLOYEE_RATE,
    EMPLOYEE_STATUS,
    EMPLOYEE_COMMENT,
    EMPLOYEE_SHIFTS,
    EMPLOYEE_TAXI,
    EMPLOYEE_REPORTS,
    EMPLOYEE_CHECKLISTS,
    EMPLOYEES_ANALYTICS,
    EMPLOYEE_AWAIT_RATE,
    EMPLOYEE_AWAIT_COMMENT,
    EMPLOYEE_DELETE_CONFIRM,
    CB_EMP_HOME,
    CB_EMP_ANALYTICS,
    CB_EMP_XLSX_ALL,
    CB_EMP_DETAIL_PREFIX,
    CB_EMP_PROFILE_PREFIX,
    CB_EMP_RATE_PREFIX,
    CB_EMP_STATUS_PREFIX,
    CB_EMP_COMMENT_PREFIX,
    CB_EMP_SHIFTS_PREFIX,
    CB_EMP_TAXI_PREFIX,
    CB_EMP_REPORTS_PREFIX,
    CB_EMP_CHECKLISTS_PREFIX,
    CB_EMP_XLSX_ONE_PREFIX,
    CB_EMP_TAXI_PHOTOS_PREFIX,
    CB_EMP_SET_STATUS_PREFIX,
    CB_EMP_BACK,
    CB_EMP_CANCEL,
    CB_EMP_DELETE,
    CB_EMP_DELETE_CONFIRM_PREFIX,
    STATUSES,
    REPORT_PERIOD_DAYS,
)

from .keyboards import (
    employees_list_keyboard,
    employee_detail_keyboard,
    edit_status_keyboard,
    taxi_photos_keyboard,
    analytics_keyboard,
    cancel_keyboard,
    confirm_delete_keyboard,
)

from .utils import (
    generate_all_employees_report,
    generate_employee_report,
    get_employee_shifts,
    get_employee_reports,
    get_employee_checklist_activity,
    get_taxi_expenses_full,
    collect_taxi_photo_ids,
    _period_range,
    delete_employee_completely,
)

logger = logging.getLogger(__name__)

MAIN_MENU_STATE = 3


# =========================================================
# HELPERS
# =========================================================

def _set_state(context, state: int) -> int:
    context.user_data["state"] = state
    return state


def _current_state(context) -> int:
    return context.user_data.get("state", MAIN_MENU_STATE)


async def _answer(query, text: str | None = None, show_alert: bool = False):
    try:
        await query.answer(text or "", show_alert=show_alert)
    except Exception:
        pass


async def _render(update, context, text, reply_markup=None, message_id=None):
    chat_id = update.effective_chat.id if update.effective_chat else None

    if chat_id and message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
            return message_id
        except Exception as e:
            if "Message is not modified" not in str(e):
                logger.warning("Edit failed: %s", e)

    if chat_id:
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
        return msg.message_id

    return None


def _short_name(user: dict) -> str:
    return (
        user.get("full_name")
        or user.get("first_name")
        or f"ID {user.get('tg_id')}"
    )


# =========================================================
# SCREENS
# =========================================================

async def show_employees_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
    notice: str | None = None,
) -> int:
    users = get_all_users()

    if not users:
        text = "👥 Команда пока пуста."
        kb = cancel_keyboard()
        await _render(update, context, text, kb, message_id)
        return _set_state(context, EMPLOYEES_LIST)

    text = (
        "👥 <b>Команда</b>\n\n"
        "Выберите сотрудника, чтобы открыть карточку."
    )

    if notice:
        text = f"{notice}\n\n{text}"

    kb = employees_list_keyboard(users)

    await _render(update, context, text, kb, message_id)

    return _set_state(context, EMPLOYEES_LIST)


async def show_employee_detail(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    tg_id: int,
    message_id: int | None = None,
    notice: str | None = None,
) -> int:
    # Сохраняем ID текущего сотрудника в контексте для удаления
    context.user_data["current_employee_id"] = tg_id

    user = get_user(tg_id)

    if not user:
        await _render(update, context, "⚠️ Сотрудник не найден.", None, message_id)
        return await show_employees_list(update, context, message_id)

    info = get_employee_full_info(tg_id) or {}

    date_from, date_to = _period_range(REPORT_PERIOD_DAYS)

    shifts = get_employee_shifts(tg_id, date_from, date_to)
    total_hours = sum((s.get("duration") or 0) / 60 for s in shifts)

    taxi = get_taxi_summary(tg_id, date_from, date_to)
    reports = get_employee_reports(tg_id, date_from, date_to)
    checklist = get_employee_checklist_activity(tg_id, date_from, date_to)

    text = (
        f"👤 <b>{_short_name(user)}</b>\n"
        f"Позиция: {info.get('position') or '—'}\n"
        f"Статус: {info.get('status') or '—'}\n\n"
        f"📊 <b>За {REPORT_PERIOD_DAYS} дней</b>\n"
        f"📆 Смен: {len(shifts)} · {round(total_hours, 1)} ч\n"
        f"🚕 Такси: {taxi.get('total') or 0} ₽\n"
        f"📋 Отчётов: {len(reports)}\n"
        f"✅ Задач: {len(checklist)}\n"
        f"💰 Ставка: {info.get('current_rate') or 0} ₽/час"
    )

    if notice:
        text = f"{notice}\n\n{text}"

    kb = employee_detail_keyboard(tg_id)

    await _render(update, context, text, kb, message_id)

    return _set_state(context, EMPLOYEE_DETAIL)


async def show_employee_profile(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    tg_id: int,
    message_id: int | None = None,
) -> int:
    info = get_employee_full_info(tg_id) or {}
    user = get_user(tg_id) or {}

    text = (
        f"👤 <b>{_short_name(user)}</b>\n\n"
        f"📌 Статус: {info.get('status') or '—'}\n"
        f"💼 Позиция: {info.get('position') or '—'}\n"
        f"📞 Телефон: {info.get('phone') or '—'}\n"
        f"🎂 ДР: {info.get('birthday') or '—'}\n"
        f"🏠 Адрес: {info.get('address') or '—'}\n"
        f"🧾 Обязанности: {info.get('responsibilities') or '—'}\n"
        f"💰 Ставка: {info.get('current_rate') or 0} ₽/час\n"
        f"📝 Комментарий: {info.get('admin_comment') or '—'}"
    )

    kb = employee_detail_keyboard(tg_id)

    await _render(update, context, text, kb, message_id)

    return _set_state(context, EMPLOYEE_PROFILE)


async def show_employee_shifts(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    tg_id: int,
    message_id: int | None = None,
) -> int:
    user = get_user(tg_id) or {}

    date_from, date_to = _period_range(REPORT_PERIOD_DAYS)
    shifts = get_employee_shifts(tg_id, date_from, date_to)

    total_hours = sum((s.get("duration") or 0) / 60 for s in shifts)

    lines = [
        f"📆 <b>Смены: {_short_name(user)}</b>",
        f"Период: {date_from} — {date_to}",
        f"Всего: {len(shifts)} смен · {round(total_hours, 1)} ч",
        "",
    ]

    if not shifts:
        lines.append("Смен за этот период нет.")
    else:
        for shift in shifts[:15]:
            lines.append(
                f"• {shift.get('date')} · {shift.get('shift_name') or '—'} · "
                f"{shift.get('location') or '—'} · {shift.get('start_time') or '—'}"
            )

        if len(shifts) > 15:
            lines.append(f"… и ещё {len(shifts) - 15}")

    kb = employee_detail_keyboard(tg_id)

    await _render(update, context, "\n".join(lines), kb, message_id)

    return _set_state(context, EMPLOYEE_SHIFTS)


async def show_employee_taxi(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    tg_id: int,
    message_id: int | None = None,
) -> int:
    user = get_user(tg_id) or {}

    date_from, date_to = _period_range(REPORT_PERIOD_DAYS)
    expenses = get_taxi_expenses_full(tg_id, date_from, date_to)

    total = sum(e.get("amount") or 0 for e in expenses)
    photos_count = sum(1 for e in expenses if e.get("photos"))

    lines = [
        f"🚕 <b>Такси: {_short_name(user)}</b>",
        f"Период: {date_from} — {date_to}",
        f"Всего: {len(expenses)} поездок · {total} ₽",
        f"С фото: {photos_count}",
        "",
    ]

    if not expenses:
        lines.append("Поездок за этот период нет.")
    else:
        for expense in expenses[:10]:
            photo_mark = " 📷" if expense.get("photos") else ""
            lines.append(f"• {expense.get('date')} · {expense.get('amount')} ₽{photo_mark}")

        if len(expenses) > 10:
            lines.append(f"… и ещё {len(expenses) - 10}")

    kb = taxi_photos_keyboard(tg_id)

    await _render(update, context, "\n".join(lines), kb, message_id)

    return _set_state(context, EMPLOYEE_TAXI)


async def show_employee_reports(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    tg_id: int,
    message_id: int | None = None,
) -> int:
    user = get_user(tg_id) or {}

    date_from, date_to = _period_range(REPORT_PERIOD_DAYS)
    reports = get_employee_reports(tg_id, date_from, date_to)

    lines = [
        f"📋 <b>Отчёты: {_short_name(user)}</b>",
        f"Период: {date_from} — {date_to}",
        f"Всего: {len(reports)}",
        "",
    ]

    if not reports:
        lines.append("Отчётов за этот период нет.")
    else:
        for report in reports[:10]:
            report_type = "Открытие" if report.get("report_type") == "opening" else "Закрытие"
            lines.append(f"• {report.get('date')} · {report_type}")

        if len(reports) > 10:
            lines.append(f"… и ещё {len(reports) - 10}")

    kb = employee_detail_keyboard(tg_id)

    await _render(update, context, "\n".join(lines), kb, message_id)

    return _set_state(context, EMPLOYEE_REPORTS)


async def show_employee_checklists(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    tg_id: int,
    message_id: int | None = None,
) -> int:
    user = get_user(tg_id) or {}

    date_from, date_to = _period_range(REPORT_PERIOD_DAYS)
    activity = get_employee_checklist_activity(tg_id, date_from, date_to)

    lines = [
        f"✅ <b>Чек-листы: {_short_name(user)}</b>",
        f"Период: {date_from} — {date_to}",
        f"Выполнено задач: {len(activity)}",
        "",
    ]

    if not activity:
        lines.append("Выполненных задач за этот период нет.")
    else:
        for act in activity[:15]:
            lines.append(f"• {act.get('date')} · {act.get('item_text') or '—'}")

        if len(activity) > 15:
            lines.append(f"… и ещё {len(activity) - 15}")

    kb = employee_detail_keyboard(tg_id)

    await _render(update, context, "\n".join(lines), kb, message_id)

    return _set_state(context, EMPLOYEE_CHECKLISTS)


async def show_analytics(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
) -> int:
    users = get_all_users()

    date_from, date_to = _period_range(REPORT_PERIOD_DAYS)

    total_shifts = 0
    total_hours = 0
    total_taxi = 0
    total_reports = 0
    total_tasks = 0

    for user in users:
        tg_id = user["tg_id"]

        shifts = get_employee_shifts(tg_id, date_from, date_to)
        total_shifts += len(shifts)
        total_hours += sum((s.get("duration") or 0) / 60 for s in shifts)

        taxi = get_taxi_summary(tg_id, date_from, date_to)
        total_taxi += taxi.get("total") or 0

        total_reports += len(get_employee_reports(tg_id, date_from, date_to))
        total_tasks += len(get_employee_checklist_activity(tg_id, date_from, date_to))

    text = (
        "📊 <b>Аналитика команды</b>\n"
        f"Период: {date_from} — {date_to}\n\n"
        f"👥 Сотрудников: {len(users)}\n"
        f"📆 Смен: {total_shifts}\n"
        f"⏱ Часов: {round(total_hours, 1)}\n"
        f"🚕 Такси: {total_taxi} ₽\n"
        f"📋 Отчётов: {total_reports}\n"
        f"✅ Задач: {total_tasks}"
    )

    kb = analytics_keyboard()

    await _render(update, context, text, kb, message_id)

    return _set_state(context, EMPLOYEES_ANALYTICS)


# =========================================================
# УДАЛЕНИЕ СОТРУДНИКА
# =========================================================

async def show_delete_confirm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    tg_id: int,
    message_id: int | None = None,
) -> int:
    user = get_user(tg_id)

    if not user:
        await _render(update, context, "⚠️ Сотрудник не найден.", None, message_id)
        return await show_employees_list(update, context, message_id)

    text = (
        f"⚠️ <b>Удаление сотрудника</b>\n\n"
        f"Вы уверены, что хотите удалить <b>{_short_name(user)}</b>?\n\n"
        "Будут удалены все данные:\n"
        "• Профиль\n"
        "• Смены\n"
        "• Такси\n"
        "• Отчёты\n"
        "• Прогресс по чек-листам\n"
        "• Ставки\n\n"
        "Это действие <b>НЕЛЬЗЯ</b> отменить!"
    )

    kb = confirm_delete_keyboard(tg_id)

    await _render(update, context, text, kb, message_id)

    return _set_state(context, EMPLOYEE_DELETE_CONFIRM)


async def delete_employee(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    tg_id: int,
    message_id: int | None = None,
) -> int:
    user = get_user(tg_id)

    if not user:
        await _render(update, context, "⚠️ Сотрудник не найден.", None, message_id)
        return await show_employees_list(update, context, message_id)

    name = _short_name(user)

    try:
        delete_employee_completely(tg_id)
        notice = f"✅ Сотрудник <b>{name}</b> удалён."
    except Exception as e:
        logger.error("Ошибка удаления сотрудника %s: %s", tg_id, e)
        notice = f"⚠️ Ошибка при удалении сотрудника {name}."

    return await show_employees_list(update, context, message_id, notice)


# =========================================================
# CALLBACK ROUTER
# =========================================================

async def employees_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data or ""
    message_id = query.message.message_id if query.message else None

    await _answer(query)

    # Домой
    if data == CB_EMP_HOME:
        try:
            from ..menu.handlers import show_main
            return await show_main(update, context, message_id)
        except Exception:
            return await show_employees_list(update, context, message_id)

    # Назад к списку
    if data == CB_EMP_BACK:
        return await show_employees_list(update, context, message_id)

    # Отмена ввода
    if data == CB_EMP_CANCEL:
        context.user_data.pop("edit_employee_id", None)
        return await show_employees_list(update, context, message_id, notice="Отменено.")

    # Аналитика
    if data == CB_EMP_ANALYTICS:
        return await show_analytics(update, context, message_id)

    # Общий XLSX
    if data == CB_EMP_XLSX_ALL:
        users = get_all_users()

        if not users:
            return await show_employees_list(update, context, message_id, notice="⚠️ Нет данных.")

        await _answer(query, "Готовлю отчёт...")

        try:
            file_bytes = generate_all_employees_report(users, REPORT_PERIOD_DAYS)

            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=file_bytes,
                filename=f"team_report_{today_msk_str()}.xlsx",
                caption="📊 Отчёт по всей команде",
            )
        except Exception as e:
            logger.error("Ошибка генерации общего отчёта: %s", e)
            return await show_analytics(update, context, message_id)

        return await show_analytics(update, context, message_id)

    # Карточка сотрудника
    if data.startswith(CB_EMP_DETAIL_PREFIX):
        tg_id = int(data.split(":")[1])
        return await show_employee_detail(update, context, tg_id, message_id)

    # Профиль
    if data.startswith(CB_EMP_PROFILE_PREFIX):
        tg_id = int(data.split(":")[1])
        return await show_employee_profile(update, context, tg_id, message_id)

    # Ставка — запрос ввода
    if data.startswith(CB_EMP_RATE_PREFIX):
        tg_id = int(data.split(":")[1])
        context.user_data["edit_employee_id"] = tg_id

        text = "💰 Отправьте новую ставку в формате:\n<code>250</code>"

        await _render(update, context, text, cancel_keyboard(), message_id)

        return _set_state(context, EMPLOYEE_AWAIT_RATE)

    # Статус — выбор
    if data.startswith(CB_EMP_STATUS_PREFIX):
        tg_id = int(data.split(":")[1])

        text = "🏷 Выберите статус:"

        await _render(update, context, text, edit_status_keyboard(tg_id), message_id)

        return _set_state(context, EMPLOYEE_STATUS)

    # Установка статуса
    if data.startswith(CB_EMP_SET_STATUS_PREFIX):
        payload = data.split(":", 1)[1]
        tg_id_str, new_status = payload.split(":", 1)
        tg_id = int(tg_id_str)

        update_employee_status(tg_id, new_status)

        return await show_employee_detail(
            update,
            context,
            tg_id,
            message_id,
            notice="✅ Статус обновлён.",
        )

    # Комментарий — запрос ввода
    if data.startswith(CB_EMP_COMMENT_PREFIX):
        tg_id = int(data.split(":")[1])
        context.user_data["edit_employee_id"] = tg_id

        text = "📝 Отправьте комментарий.\nОтправьте <code>-</code>, чтобы удалить."

        await _render(update, context, text, cancel_keyboard(), message_id)

        return _set_state(context, EMPLOYEE_AWAIT_COMMENT)

    # Смены
    if data.startswith(CB_EMP_SHIFTS_PREFIX):
        tg_id = int(data.split(":")[1])
        return await show_employee_shifts(update, context, tg_id, message_id)

    # Такси
    if data.startswith(CB_EMP_TAXI_PREFIX):
        tg_id = int(data.split(":")[1])
        return await show_employee_taxi(update, context, tg_id, message_id)

    # Отчёты
    if data.startswith(CB_EMP_REPORTS_PREFIX):
        tg_id = int(data.split(":")[1])
        return await show_employee_reports(update, context, tg_id, message_id)

    # Чек-листы
    if data.startswith(CB_EMP_CHECKLISTS_PREFIX):
        tg_id = int(data.split(":")[1])
        return await show_employee_checklists(update, context, tg_id, message_id)

    # XLSX по одному
    if data.startswith(CB_EMP_XLSX_ONE_PREFIX):
        tg_id = int(data.split(":")[1])

        await _answer(query, "Готовлю отчёт...")

        try:
            file_bytes = generate_employee_report(tg_id, REPORT_PERIOD_DAYS)

            user = get_user(tg_id) or {}
            file_name = f"employee_{tg_id}_{today_msk_str()}.xlsx"

            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=file_bytes,
                filename=file_name,
                caption=f"📊 Отчёт: {_short_name(user)}",
            )
        except Exception as e:
            logger.error("Ошибка генерации отчёта по сотруднику: %s", e)

        return await show_employee_detail(update, context, tg_id, message_id)

    # Фото такси
    if data.startswith(CB_EMP_TAXI_PHOTOS_PREFIX):
        tg_id = int(data.split(":")[1])

        photo_ids = collect_taxi_photo_ids(tg_id, REPORT_PERIOD_DAYS)

        if not photo_ids:
            return await show_employee_taxi(update, context, tg_id, message_id)

        chat_id = update.effective_chat.id

        try:
            for start in range(0, len(photo_ids), 10):
                chunk = photo_ids[start:start + 10]

                media_group = [
                    InputMediaPhoto(media=photo_id)
                    for photo_id in chunk
                ]

                await context.bot.send_media_group(chat_id=chat_id, media=media_group)
        except Exception as e:
            logger.error("Ошибка отправки фото такси: %s", e)

        return await show_employee_taxi(update, context, tg_id, message_id)

    # УДАЛЕНИЕ СОТРУДНИКА
    if data == CB_EMP_DELETE:
        tg_id = context.user_data.get("current_employee_id")
        if not tg_id:
            return await show_employees_list(update, context, message_id, notice="⚠️ Ошибка: сотрудник не выбран.")

        return await show_delete_confirm(update, context, tg_id, message_id)

    # ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ
    if data.startswith(CB_EMP_DELETE_CONFIRM_PREFIX):
        tg_id = int(data.split(":")[1])
        return await delete_employee(update, context, tg_id, message_id)

    return await show_employees_list(update, context, message_id)


# =========================================================
# TEXT INPUT (ставка / комментарий)
# =========================================================

async def employee_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user

    if not user:
        return MAIN_MENU_STATE

    text = (update.message.text or "").strip()

    if not text:
        await update.message.reply_text("⚠️ Пустой ввод.")
        return _current_state(context)

    state = _current_state(context)
    tg_id = context.user_data.get("edit_employee_id")

    if not tg_id:
        await update.message.reply_text("⚠️ Начните заново.")
        return MAIN_MENU_STATE

    # Ставка
    if state == EMPLOYEE_AWAIT_RATE:
        try:
            rate = float(text.replace(",", "."))

            if rate < 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("⚠️ Введите положительное число.")
            return state

        set_salary_rate(tg_id, rate, today_msk_str())

        context.user_data.pop("edit_employee_id", None)

        return await show_employee_detail(
            update,
            context,
            tg_id,
            notice=f"✅ Ставка обновлена: {rate} ₽/час",
        )

    # Комментарий
    if state == EMPLOYEE_AWAIT_COMMENT:
        comment = None if text == "-" else text

        update_employee_comment(tg_id, comment)

        context.user_data.pop("edit_employee_id", None)

        return await show_employee_detail(
            update,
            context,
            tg_id,
            notice="✅ Комментарий обновлён.",
        )

    return state