from telegram.ext import ContextTypes
from telegram.error import TelegramError

# ID закрытого канала, куда будут отправляться фото
PHOTO_CHANNEL_ID = -1004343960839


async def send_photo_to_channel(
    context: ContextTypes.DEFAULT_TYPE,
    photo_file_id: str,
    caption: str | None = None,
) -> int:
    """
    Отправляет фото в закрытый канал и возвращает message_id.

    Фото не скачивается на сервер.
    Используется file_id, полученный от Telegram.
    """
    if caption and len(caption) > 1000:
        caption = caption[:1000] + "…"

    message = await context.bot.send_photo(
        chat_id=PHOTO_CHANNEL_ID,
        photo=photo_file_id,
        caption=caption,
    )

    return message.message_id