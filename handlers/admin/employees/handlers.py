import logging
from telegram import Update
from telegram.ext import ContextTypes

from db.users import get_all_users, get_user
from db.profile import (
    get_employee_full_info,
    update_employee_status,
    update_employee_comment,
    set_salary_rate,
    get_taxi_summary,        # <-- добавлено, если используется
)
from utils.time_utils import today_msk_str

from .constants import (
    EMPLOYEES_LIST,
    EMPLOYEE_DETAIL,
    EMPLOYEE_EDIT_STATUS,
    EMPLOYEE_EDIT_COMMENT,
    EMPLOYEE_EDIT_RATE,
    CB_EMPLOYEES_BACK,
    CB_EMPLOYEES_REPORT_ALL,
    CB_EMPLOYEE_DETAIL_PREFIX,
    CB_EMPLOYEE_EDIT_STATUS_PREFIX,
    CB_EMPLOYEE_EDIT_COMMENT_PREFIX,
    CB_EMPLOYEE_EDIT_RATE_PREFIX,
    CB_EMPLOYEE_REPORT_PREFIX,
    CB_EMPLOYEE_CANCEL,
    STATUSES,
)
from .keyboards import (
    employees_list_keyboard,
    employee_detail_keyboard,
    edit_status_keyboard,
    cancel_keyboard,
)
from .utils import generate_all_employees_report, generate_employee_report

from ..menu.utils import render, answer, set_state, get_current_state

logger = logging.getLogger(__name__)
MAIN_MENU_STATE = 100


async def show_employees_list(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int | None = None, notice: str | None = None) -> int:
    users = get_all_users()
    if not users:
        text = "👥 Сотрудники не найдены."
        kb = cancel_keyboard()
        await render(update, context, text, kb, message_id)
        return EMPLOYEES_LIST

    text = "👥 Список сотрудников:\n\nНажмите на имя для просмотра деталей."
    if notice:
        text = f"{notice}\n\n{text}"
    kb = employees_list_keyboard(users)
    await render(update, context, text, kb, message_id)
    return set_state(context, EMPLOYEES_LIST)


async def show_employee_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, tg_id: int, message_id: int | None = None, notice: str | None = None) -> int:
    user = get_employee_full_info(tg_id)
    if not user:
        await render(update, context, "⚠️ Сотрудник не найден.", None, message_id)
        return await show_employees_list(update, context, message_id)

    text = (
        f"👤 <b>Сотрудник</b>\n\n"
        f"<b>ФИО:</b> {user.get('full_name', '—')}\n"
        f"<b>Позиция:</b> {user.get('position', '—')}\n"
        f"<b>Телефон:</b> {user.get('phone', '—')}\n"
        f"<b>Дата рождения:</b> {user.get('birthday', '—')}\n"
        f"<b>Статус:</b> {user.get('status', 'Сотрудник')}\n"
        f"<b>Комментарий:</b> {user.get('admin_comment', '—')}\n"
        f"<b>Ставка:</b> {user.get('current_rate', 0):.2f} ₽/час"
    )
    if notice:
        text = f"{notice}\n\n{text}"

    kb = employee_detail_keyboard(tg_id, user.get('status', 'Сотрудник'), user.get('current_rate', 0))
    await render(update, context, text, kb, message_id, parse_mode='HTML')
    return set_state(context, EMPLOYEE_DETAIL)


async def employees_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data or ""
    message_id = query.message.message_id if query.message else None
    await answer(query)

    if data == CB_EMPLOYEES_BACK:
        from ..menu.handlers import show_main
        return await show_main(update, context, message_id)

    if data == CB_EMPLOYEES_REPORT_ALL:
        users = get_all_users()
        if not users:
            await render(update, context, "⚠️ Нет сотрудников для отчёта.", None, message_id)
            return EMPLOYEES_LIST
        try:
            report_data = generate_all_employees_report(users)
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=report_data,
                filename=f"employees_report_{today_msk_str()}.xlsx",
                caption="📊 Отчёт по всем сотрудникам"
            )
        except Exception as e:
            logger.error("Ошибка генерации отчёта: %s", e)
            await render(update, context, "⚠️ Не удалось сгенерировать отчёт.", None, message_id)
        return EMPLOYEES_LIST

    if data.startswith(CB_EMPLOYEE_DETAIL_PREFIX):
        tg_id = int(data.split(":")[1])
        return await show_employee_detail(update, context, tg_id, message_id)

    if data.startswith(CB_EMPLOYEE_EDIT_STATUS_PREFIX):
        tg_id = int(data.split(":")[1])
        text = "Выберите новый статус:"
        kb = edit_status_keyboard(tg_id)
        await render(update, context, text, kb, message_id)
        return set_state(context, EMPLOYEE_EDIT_STATUS)

    if data.startswith("emp_set_status:"):
        parts = data.split(":")
        tg_id = int(parts[1])
        new_status = parts[2]
        update_employee_status(tg_id, new_status)
        return await show_employee_detail(update, context, tg_id, message_id, notice="✅ Статус обновлён")

    if data.startswith(CB_EMPLOYEE_EDIT_COMMENT_PREFIX):
        tg_id = int(data.split(":")[1])
        context.user_data["edit_employee_id"] = tg_id
        text = "✏️ Введите новый комментарий для сотрудника (или отправьте '-' для удаления):"
        kb = cancel_keyboard()
        await render(update, context, text, kb, message_id)
        return set_state(context, EMPLOYEE_EDIT_COMMENT)

    if data.startswith(CB_EMPLOYEE_EDIT_RATE_PREFIX):
        tg_id = int(data.split(":")[1])
        context.user_data["edit_employee_id"] = tg_id
        text = "💰 Введите новую ставку (в рублях за час):"
        kb = cancel_keyboard()
        await render(update, context, text, kb, message_id)
        return set_state(context, EMPLOYEE_EDIT_RATE)

    if data.startswith(CB_EMPLOYEE_REPORT_PREFIX):
        tg_id = int(data.split(":")[1])
        try:
            report_data = generate_employee_report(tg_id)
            if not report_data:
                await render(update, context, "⚠️ Не удалось сгенерировать отчёт.", None, message_id)
                return EMPLOYEE_DETAIL
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=report_data,
                filename=f"employee_{tg_id}_{today_msk_str()}.xlsx",
                caption="📊 Отчёт по сотруднику"
            )
        except Exception as e:
            logger.error("Ошибка генерации отчёта по сотруднику: %s", e)
            await render(update, context, "⚠️ Ошибка при создании отчёта.", None, message_id)
        return await show_employee_detail(update, context, tg_id, message_id)

    if data == CB_EMPLOYEE_CANCEL:
        context.user_data.pop("edit_employee_id", None)
        return await show_employees_list(update, context, message_id, notice="Отменено")

    return await show_employees_list(update, context, message_id)


async def employee_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU_STATE

    text = (update.message.text or "").strip()
    chat_id = update.effective_chat.id
    if not text:
        await update.message.reply_text("⚠️ Текст не может быть пустым.")
        return get_current_state(context)

    state = get_current_state(context)
    tg_id = context.user_data.get("edit_employee_id")
    if not tg_id:
        await update.message.reply_text("⚠️ Ошибка: не выбран сотрудник. Начните заново.")
        return MAIN_MENU_STATE

    if state == EMPLOYEE_EDIT_COMMENT:
        comment = None if text == "-" else text
        update_employee_comment(tg_id, comment)
        context.user_data.pop("edit_employee_id", None)
        await update.message.reply_text("✅ Комментарий обновлён!")
        return await show_employee_detail(update, context, tg_id, chat_id, notice="✅ Комментарий обновлён")

    elif state == EMPLOYEE_EDIT_RATE:
        try:
            rate = float(text.replace(",", "."))
            if rate < 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("⚠️ Введите положительное число.")
            return state
        set_salary_rate(tg_id, rate, today_msk_str())
        context.user_data.pop("edit_employee_id", None)
        await update.message.reply_text(f"✅ Ставка обновлена до {rate:.2f} ₽/час")
        return await show_employee_detail(update, context, tg_id, chat_id, notice=f"✅ Ставка обновлена до {rate:.2f} ₽/час")

    return state