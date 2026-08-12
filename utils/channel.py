from telegram.ext import ContextTypes
from telegram import InputMediaPhoto, InputMediaVideo
from telegram.error import TelegramError
import logging

logger = logging.getLogger(__name__)

# ID закрытого канала, куда будут отправляться фото и видео
PHOTO_CHANNEL_ID = -1004343960839


async def send_photo_to_channel(
    context: ContextTypes.DEFAULT_TYPE,
    photo_file_id: str,
    caption: str | None = None,
) -> int:
    """
    Отправляет одно фото в канал и возвращает message_id.
    """
    if caption and len(caption) > 1000:
        caption = caption[:1000] + "…"

    logger.info(f"📤 Отправка одиночного фото в канал {PHOTO_CHANNEL_ID}, file_id={photo_file_id[:20]}...")
    message = await context.bot.send_photo(
        chat_id=PHOTO_CHANNEL_ID,
        photo=photo_file_id,
        caption=caption,
    )
    logger.info(f"✅ Фото отправлено, message_id={message.message_id}")
    return message.message_id


async def send_media_group_to_channel(
    context: ContextTypes.DEFAULT_TYPE,
    media_items: list[dict],   # [{"type": "photo", "file_id": "..."}, ...]
    caption: str | None = None,
) -> list[int]:
    """
    Отправляет альбом (медиагруппу) в канал, возвращает список message_id.
    Поддерживает фото и видео.
    """
    if not media_items:
        logger.warning("⚠️ Попытка отправить пустой альбом")
        return []

    logger.info(f"📤 Отправка альбома в канал {PHOTO_CHANNEL_ID}, количество файлов: {len(media_items)}")

    # Ограничение Telegram: не более 10 элементов в одной группе
    if len(media_items) > 10:
        logger.warning(f"⚠️ Альбом содержит {len(media_items)} файлов, обрезаем до 10")
        media_items = media_items[:10]

    media_group = []
    for i, item in enumerate(media_items):
        media_type = item.get("type")
        file_id = item.get("file_id")
        if not file_id:
            continue

        # Подпись только для первого элемента, обрезаем до 1024 символов
        item_caption = caption[:1024] if i == 0 and caption else None

        if media_type == "photo":
            media = InputMediaPhoto(media=file_id, caption=item_caption)
        elif media_type == "video":
            media = InputMediaVideo(media=file_id, caption=item_caption)
        else:
            continue

        media_group.append(media)

    if not media_group:
        logger.warning("⚠️ Не удалось сформировать медиагруппу")
        return []

    try:
        messages = await context.bot.send_media_group(
            chat_id=PHOTO_CHANNEL_ID,
            media=media_group,
        )
        message_ids = [msg.message_id for msg in messages]
        logger.info(f"✅ Альбом отправлен, получены message_id: {message_ids}")
        return message_ids
    except TelegramError as e:
        logger.error(f"❌ Ошибка отправки альбома: {e}")
        raise