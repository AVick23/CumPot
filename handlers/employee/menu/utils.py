from .constants import LOCATIONS, MSG_LIMIT, MAIN_MENU  # добавил импорт MAIN_MENU
from telegram.error import BadRequest
import logging

logger = logging.getLogger(__name__)


def get_position_label(position: str | None) -> str:
    return LOCATIONS.get(position, position or "—")


def main_menu_text(user_db: dict, shift: dict | None) -> str:
    full_name = user_db.get("full_name") or "Сотрудник"

    if shift:
        shift_location_label = get_position_label(shift.get("location"))
        shift_name = shift.get("shift_name", "")
        shift_start = shift.get("shift_start_time") or shift.get("start_time") or "—"
        if shift_name:
            return (
                "🟢 Смена открыта\n"
                f"📍 {shift_location_label} · {shift_name} (с {shift_start})\n\n"
                "Смена закроется автоматически после 00:00 по МСК.\n"
                "Выберите действие."
            )
        else:
            return (
                "🟢 Смена открыта\n"
                f"📍 {shift_location_label} · с {shift_start}\n\n"
                "Смена закроется автоматически после 00:00 по МСК.\n"
                "Выберите действие."
            )

    position_label = get_position_label(user_db.get("position"))

    return (
        f"👋 {full_name}\n"
        f"Ваша позиция: {position_label}\n\n"
        "Сейчас вы не на смене.\n"
        "Когда будете готовы, начните смену."
    )


def truncate_text(text: str | None, limit: int = MSG_LIMIT) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + "…"


async def render(update, context, text, reply_markup=None, message_id=None):
    """Отправляет или редактирует сообщение."""
    text = truncate_text(text, MSG_LIMIT)
    chat_id = update.effective_chat.id if update.effective_chat else None

    if chat_id and message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
            )
            return message_id
        except BadRequest as e:
            if "Message is not modified" in str(e):
                return message_id
            logger.warning("Edit failed: %s", e)

    if chat_id:
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
        )
        return msg.message_id
    return None


async def cleanup_message(context, chat_id, message_id, fallback_text="✅ Готово"):
    if not chat_id or not message_id:
        return
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        return
    except Exception:
        pass
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=fallback_text,
            reply_markup=None,
        )
    except Exception:
        pass


async def answer(query, text: str | None = None, show_alert: bool = False):
    try:
        await query.answer(text or "", show_alert=show_alert)
    except Exception:
        pass


# ===== ИСПРАВЛЕНИЕ: используем "state" вместо "employee_state" =====
def set_state(context, state: int) -> int:
    context.user_data["state"] = state   # было "employee_state"
    return state


def get_current_state(context) -> int:
    return context.user_data.get("state", MAIN_MENU)   # было "employee_state"