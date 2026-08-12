from telegram.ext import ContextTypes
from telegram import InputMediaPhoto, InputMediaVideo
from telegram.error import TelegramError

# ID закрытого канала, куда будут отправляться фото и видео
PHOTO_CHANNEL_ID = -1004343960839


async def send_photo_to_channel(
    context: ContextTypes.DEFAULT_TYPE,
    photo_file_id: str,
    caption: str | None = None,
) -> int:
    """
    Отправляет одно фото в канал и возвращает message_id.
    Сохранено для обратной совместимости.
    """
    if caption and len(caption) > 1000:
        caption = caption[:1000] + "…"

    message = await context.bot.send_photo(
        chat_id=PHOTO_CHANNEL_ID,
        photo=photo_file_id,
        caption=caption,
    )
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
        return []

    # Ограничение Telegram: не более 10 элементов в одной группе
    if len(media_items) > 10:
        media_items = media_items[:10]

    media_group = []
    for i, item in enumerate(media_items):
        media_type = item.get("type")
        file_id = item.get("file_id")
        if not file_id:
            continue

        if media_type == "photo":
            media = InputMediaPhoto(media=file_id)
        elif media_type == "video":
            media = InputMediaVideo(media=file_id)
        else:
            continue

        # Подпись только для первого элемента
        if i == 0 and caption:
            media.caption = caption[:1000]  # ограничение длины подписи

        media_group.append(media)

    if not media_group:
        return []

    try:
        messages = await context.bot.send_media_group(
            chat_id=PHOTO_CHANNEL_ID,
            media=media_group,
        )
        return [msg.message_id for msg in messages]
    except TelegramError as e:
        # Если не удалось отправить группу, пробуем отправить по одному
        # или просто логируем ошибку
        raise