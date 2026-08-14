from telegram.error import BadRequest
import logging
from .constants import MSG_LIMIT

logger = logging.getLogger(__name__)


def truncate_text(text: str | None, limit: int = MSG_LIMIT) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + "…"


async def render(update, context, text, reply_markup=None, message_id=None, parse_mode=None):
    """Отправляет или редактирует сообщение с поддержкой parse_mode."""
    text = truncate_text(text, MSG_LIMIT)
    chat_id = update.effective_chat.id if update.effective_chat else None

    if chat_id and message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
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
            parse_mode=parse_mode,
        )
        return msg.message_id
    return None


async def answer(query, text: str | None = None, show_alert: bool = False):
    """Отвечает на callback query."""
    try:
        await query.answer(text or "", show_alert=show_alert)
    except Exception:
        pass


def set_state(context, state: int) -> int:
    context.user_data["state"] = state
    return state


def get_current_state(context) -> int:
    return context.user_data.get("state", 100)  # ADMIN_MAIN