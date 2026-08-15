import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from db import get_connection
from db.users import get_active_users, get_user, deactivate_user, activate_user
from db.profile import (
    get_employee_full_info,
    update_employee_status,
    update_employee_comment,
)

from utils.time_utils import today_msk_str

from .constants import (
    EMPLOYEES_LIST,
    EMPLOYEE_HIDDEN_LIST,
    EMPLOYEE_DETAIL,
    EMPLOYEE_PROFILE,
    EMPLOYEE_STATUS,
    EMPLOYEE_COMMENT,
    EMPLOYEE_SHIFTS,
    EMPLOYEE_REPORTS,
    EMPLOYEE_CHECKLISTS,
    EMPLOYEES_ANALYTICS,
    EMPLOYEE_AWAIT_COMMENT,
    EMPLOYEE_DELETE_CONFIRM,
    CB_EMP_HOME,
    CB_EMP_ANALYTICS,
    CB_EMP_XLSX_ALL,
    CB_EMP_XLSX_ONE_PREFIX,
    CB_EMP_DETAIL_PREFIX,
    CB_EMP_PROFILE_PREFIX,
    CB_EMP_STATUS_PREFIX,
    CB_EMP_COMMENT_PREFIX,
    CB_EMP_SHIFTS_PREFIX,
    CB_EMP_REPORTS_PREFIX,
    CB_EMP_CHECKLISTS_PREFIX,
    CB_EMP_SET_STATUS_PREFIX,
    CB_EMP_BACK,
    CB_EMP_CANCEL,
    CB_EMP_DELETE,
    CB_EMP_DELETE_SOFT,
    CB_EMP_DELETE_HARD,
    CB_EMP_HIDDEN,
    CB_EMP_RESTORE_PREFIX,
    REPORT_PERIOD_DAYS,
)

from .keyboards import (
    employees_list_keyboard,
    hidden_list_keyboard,
    employee_detail_keyboard,
    edit_status_keyboard,
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
    users = get_active_users()

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM users WHERE is_active = 0 ORDER BY full_name, first_name"
        ).fetchall()
        hidden_users = [dict(row) for row in rows]

    has_hidden = bool(hidden_users)

    if not users:
        text = "👥 Команда пока пуста."

        if has_hidden:
            kb = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🙈 Скрытые сотрудники", callback_data=CB_EMP_HIDDEN)],
                    [InlineKeyboardButton("🏠 Меню", callback_data=CB_EMP_HOME)],
                ]
            )
        else:
            kb = cancel_keyboard()

        await _render(update, context, text, kb, message_id)
        return _set_state(context, EMPLOYEES_LIST)

    text = (
        "👥 <b>Команда</b>\n\n"
        "Выберите сотрудника, чтобы открыть карточку."
    )

    if notice:
        text = f"{notice}\n\n{text}"

    kb = employees_list_keyboard(users, has_hidden)
    await _render(update, context, text, kb, message_id)
    return _set_state(context, EMPLOYEES_LIST)


async def show_hidden_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
    notice: str | None = None,
) -> int:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM users WHERE is_active = 0 ORDER BY full_name, first_name"
        ).fetchall()
        users = [dict(row) for row in rows]

    if not users:
        text = "🙈 Скрытых сотрудников нет."
        kb = cancel_keyboard()
        await _render(update, context, text, kb, message_id)
        return _set_state(context, EMPLOYEE_HIDDEN_LIST)

    text = "🙈 <b>Скрытые сотрудники</b>\n\nНажмите на имя, чтобы открыть карточку, или используйте кнопки действий ниже."

    if notice:
        text = f"{notice}\n\n{text}"

    kb = hidden_list_keyboard(users)
    await _render(update, context, text, kb, message_id)
    return _set_state(context, EMPLOYEE_HIDDEN_LIST)


async def show_employee_detail(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    tg_id: int,
    message_id: int | None = None,
    notice: str | None = None,
) -> int:
    context.user_data["current_employee_id"] = tg_id
    user = get_user(tg_id)

    if not user:
        await _render(update, context, "⚠️ Сотрудник не найден.", None, message_id)
        return await show_employees_list(update, context, message_id)

    if user.get("is_active") == 0:
        notice = (notice or "") + "\n\n⚠️ Сотрудник скрыт из списка."

    info = get_employee_full_info(tg_id) or {}

    date_from, date_to = _period_range(REPORT_PERIOD_DAYS)
    shifts = get_employee_shifts(tg_id, date_from, date_to)
    total_hours = sum((s.get("duration") or 0) / 60 for s in shifts)
    reports = get_employee_reports(tg_id, date_from, date_to)
    checklist = get_employee_checklist_activity(tg_id, date_from, date_to)

    text = (
        f"👤 <b>{_short_name(user)}</b>\n"
        f"Позиция: {info.get('position') or '—'}\n"
        f"Статус: {info.get('status') or '—'}\n\n"
        f"📊 <b>За {REPORT_PERIOD_DAYS} дней</b>\n"
        f"📆 Смен: {len(shifts)} · {round(total_hours, 1)} ч\n"
        f"📋 Отчётов: {len(reports)}\n"
        f"✅ Задач: {len(checklist)}"
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
    users = get_active_users()
    date_from, date_to = _period_range(REPORT_PERIOD_DAYS)

    total_shifts = 0
    total_hours = 0
    total_reports = 0
    total_tasks = 0

    for user in users:
        tg_id = user["tg_id"]

        shifts = get_employee_shifts(tg_id, date_from, date_to)
        total_shifts += len(shifts)
        total_hours += sum((s.get("duration") or 0) / 60 for s in shifts)

        total_reports += len(get_employee_reports(tg_id, date_from, date_to))
        total_tasks += len(get_employee_checklist_activity(tg_id, date_from, date_to))

    text = (
        "📊 <b>Аналитика команды</b>\n"
        f"Период: {date_from} — {date_to}\n\n"
        f"👥 Сотрудников: {len(users)}\n"
        f"📆 Смен: {total_shifts}\n"
        f"⏱ Часов: {round(total_hours, 1)}\n"
        f"📋 Отчётов: {total_reports}\n"
        f"✅ Задач: {total_tasks}"
    )

    kb = analytics_keyboard()
    await _render(update, context, text, kb, message_id)
    return _set_state(context, EMPLOYEES_ANALYTICS)


# =========================================================
# УДАЛЕНИЕ И ВОССТАНОВЛЕНИЕ
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
        "Выберите способ удаления:\n"
        "• <b>Удалить полностью</b> – все данные будут безвозвратно стёрты.\n"
        "• <b>Скрыть из списка</b> – сотрудник исчезнет из команды, но все его данные сохранятся.\n\n"
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
    hard: bool = True,
) -> int:
    user = get_user(tg_id)

    if not user:
        await _render(update, context, "⚠️ Сотрудник не найден.", None, message_id)
        return await show_employees_list(update, context, message_id)

    name = _short_name(user)

    if hard:
        try:
            delete_employee_completely(tg_id)
            notice = f"✅ Сотрудник <b>{name}</b> полностью удалён."
        except Exception as e:
            logger.error("Ошибка полного удаления %s: %s", tg_id, e)
            notice = f"⚠️ Ошибка при удалении сотрудника {name}."
    else:
        try:
            deactivate_user(tg_id)
            notice = f"🙈 Сотрудник <b>{name}</b> скрыт из списка. Данные сохранены."
        except Exception as e:
            logger.error("Ошибка скрытия %s: %s", tg_id, e)
            notice = f"⚠️ Ошибка при скрытии сотрудника {name}."

    return await show_employees_list(update, context, message_id, notice)


async def restore_employee(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    tg_id: int,
    message_id: int | None = None,
) -> int:
    user = get_user(tg_id)

    if not user:
        await _render(update, context, "⚠️ Сотрудник не найден.", None, message_id)
        return await show_hidden_list(update, context, message_id)

    name = _short_name(user)

    try:
        activate_user(tg_id)
        notice = f"✅ Сотрудник <b>{name}</b> восстановлен."
    except Exception as e:
        logger.error("Ошибка восстановления %s: %s", tg_id, e)
        notice = f"⚠️ Ошибка при восстановлении сотрудника {name}."

    return await show_hidden_list(update, context, message_id, notice)


# =========================================================
# CALLBACK ROUTER
# =========================================================
async def employees_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data or ""
    message_id = query.message.message_id if query.message else None

    await _answer(query)

    # --- Навигация ---
    if data == CB_EMP_HOME:
        try:
            from ..menu.handlers import show_main
            return await show_main(update, context, message_id)
        except Exception:
            return await show_employees_list(update, context, message_id)

    if data == CB_EMP_BACK:
        state = _current_state(context)
        if state == EMPLOYEE_HIDDEN_LIST:
            return await show_employees_list(update, context, message_id)
        return await show_employees_list(update, context, message_id)

    if data == CB_EMP_CANCEL:
        context.user_data.pop("edit_employee_id", None)
        return await show_employees_list(update, context, message_id, notice="Отменено.")

    # --- Скрытые ---
    if data == CB_EMP_HIDDEN:
        return await show_hidden_list(update, context, message_id)

    if data.startswith(CB_EMP_RESTORE_PREFIX):
        tg_id = int(data.split(":")[1])
        return await restore_employee(update, context, tg_id, message_id)

    # --- Удаление ---
    if data.startswith(CB_EMP_DELETE_HARD):
        tg_id = int(data.split(":")[1])
        return await show_delete_confirm(update, context, tg_id, message_id)

    if data.startswith(CB_EMP_DELETE_SOFT):
        tg_id = int(data.split(":")[1])
        return await delete_employee(update, context, tg_id, message_id, hard=False)

    # --- Аналитика ---
    if data == CB_EMP_ANALYTICS:
        return await show_analytics(update, context, message_id)

    if data == CB_EMP_XLSX_ALL:
        users = get_active_users()

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

    # --- Карточка сотрудника ---
    if data.startswith(CB_EMP_DETAIL_PREFIX):
        tg_id = int(data.split(":")[1])
        return await show_employee_detail(update, context, tg_id, message_id)

    # --- Профиль ---
    if data.startswith(CB_EMP_PROFILE_PREFIX):
        tg_id = int(data.split(":")[1])
        return await show_employee_profile(update, context, tg_id, message_id)

    # --- Статус ---
    if data.startswith(CB_EMP_STATUS_PREFIX):
        tg_id = int(data.split(":")[1])
        text = "🏷 Выберите статус:"
        await _render(update, context, text, edit_status_keyboard(tg_id), message_id)
        return _set_state(context, EMPLOYEE_STATUS)

    if data.startswith(CB_EMP_SET_STATUS_PREFIX):
        payload = data.split(":", 1)[1]
        tg_id_str, new_status = payload.split(":", 1)
        tg_id = int(tg_id_str)
        update_employee_status(tg_id, new_status)
        return await show_employee_detail(update, context, tg_id, message_id, notice="✅ Статус обновлён.")

    # --- Комментарий ---
    if data.startswith(CB_EMP_COMMENT_PREFIX):
        tg_id = int(data.split(":")[1])
        context.user_data["edit_employee_id"] = tg_id
        text = "📝 Отправьте комментарий.\nОтправьте <code>-</code>, чтобы удалить."
        await _render(update, context, text, cancel_keyboard(), message_id)
        return _set_state(context, EMPLOYEE_AWAIT_COMMENT)

    # --- Смены ---
    if data.startswith(CB_EMP_SHIFTS_PREFIX):
        tg_id = int(data.split(":")[1])
        return await show_employee_shifts(update, context, tg_id, message_id)

    # --- Отчёты ---
    if data.startswith(CB_EMP_REPORTS_PREFIX):
        tg_id = int(data.split(":")[1])
        return await show_employee_reports(update, context, tg_id, message_id)

    # --- Чек-листы ---
    if data.startswith(CB_EMP_CHECKLISTS_PREFIX):
        tg_id = int(data.split(":")[1])
        return await show_employee_checklists(update, context, tg_id, message_id)

    # --- XLSX по одному ---
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

    # --- Удаление (основное меню) ---
    if data == CB_EMP_DELETE:
        tg_id = context.user_data.get("current_employee_id")

        if not tg_id:
            return await show_employees_list(
                update,
                context,
                message_id,
                notice="⚠️ Ошибка: сотрудник не выбран.",
            )

        return await show_delete_confirm(update, context, tg_id, message_id)

    # Fallback
    return await show_employees_list(update, context, message_id)


# =========================================================
# TEXT INPUT (комментарий)
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