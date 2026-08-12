import logging
import json
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from utils.channel import send_photo_to_channel, send_media_group_to_channel
from db.users import get_user
from .utils import (
    set_state,
    answer,
    render,
    cleanup_message,
    get_checklist_items,
    get_categories_stats,
    get_items_by_category,
    get_item_by_id,
    toggle_item,
    attach_media_to_task,
    get_user_progress_summary,
    progress_bar,
    percent,
    item_detail_text,
    build_photo_caption,
)
from .constants import (
    CATEGORY_SELECT,
    CHECKLIST_VIEW,
    ITEM_DETAIL,
    PROGRESS_VIEW,
    AWAIT_TASK_PHOTO,
    CATEGORY_NAMES,
    CB_CATEGORY_PREFIX,
    CB_ITEM_PREFIX,
    CB_TOGGLE_PREFIX,
    CB_PHOTO_PREFIX,
    CB_VIEW_PHOTO_PREFIX,
    CB_PHOTO_CANCEL,
    CB_BACK_MENU,
    CB_BACK_CATEGORIES,
    CB_PHOTO_DONE,
)
from .keyboards import (
    categories_keyboard,
    checklist_keyboard,
    item_detail_keyboard,
    progress_keyboard,
    photo_prompt_keyboard,
)

MAIN_MENU = 3

logger = logging.getLogger(__name__)

# Хранилище для собираемых альбомов (media_group_id -> данные)
_album_buffer: dict[str, dict] = {}


async def show_categories(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
    notice: str | None = None,
) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU

    items = get_checklist_items(user.id)
    if items is None:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ В меню", callback_data=CB_BACK_MENU)]])
        await render(update, context, "Сначала начните смену.", kb, message_id)
        return CATEGORY_SELECT

    stats = get_categories_stats(user.id)
    if not stats:
        text = "📋 Чек-лист\n\nНа сегодня задач нет."
        if notice:
            text = f"{notice}\n\n{text}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ В меню", callback_data=CB_BACK_MENU)]])
        await render(update, context, text, kb, message_id)
        return set_state(context, CATEGORY_SELECT)

    text = "📋 Чек-лист\n\nВыберите категорию."
    if notice:
        text = f"{notice}\n\n{text}"

    kb = categories_keyboard(stats)
    await render(update, context, text, kb, message_id)

    return set_state(context, CATEGORY_SELECT)


async def category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data or ""

    await answer(query)

    message_id = query.message.message_id if query.message else None

    if data.startswith(CB_CATEGORY_PREFIX):
        category = data.split(":", 1)[1]
        context.user_data["current_category"] = category
        return await show_checklist(update, context, category, message_id)

    if data == CB_BACK_MENU:
        return MAIN_MENU

    return await show_categories(update, context, message_id)


async def show_checklist(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    category: str,
    message_id: int | None = None,
    notice: str | None = None,
) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU

    items = get_items_by_category(user.id, category)

    if items is None:
        await render(update, context, "Сначала начните смену.", None, message_id)
        return CATEGORY_SELECT

    if not items:
        return await show_categories(update, context, message_id, notice="В этой категории нет задач.")

    context.user_data["current_category"] = category

    done = sum(1 for item in items if item.get("completed"))
    total = len(items)

    bar = progress_bar(done, total)
    category_label = CATEGORY_NAMES.get(category, category)

    text = (
        f"📋 {category_label}\n"
        f"{bar} {done}/{total} · {percent(done, total)}%\n\n"
        "Нажмите на задачу, чтобы открыть её."
    )

    if notice:
        text = f"{notice}\n\n{text}"

    kb = checklist_keyboard(items)
    await render(update, context, text, kb, message_id)

    return set_state(context, CHECKLIST_VIEW)


async def show_current_checklist(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
    notice: str | None = None,
) -> int:
    category = context.user_data.get("current_category")

    if not category:
        return await show_categories(update, context, message_id, notice)

    return await show_checklist(update, context, category, message_id, notice)


async def show_item_detail(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    item_id: int,
    message_id: int | None = None,
    notice: str | None = None,
) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU

    item = get_item_by_id(user.id, item_id)

    if not item:
        return await show_current_checklist(update, context, message_id, notice="⚠️ Задача не найдена.")

    text = item_detail_text(item)

    if notice:
        text = f"{notice}\n\n{text}"

    kb = item_detail_keyboard(
        item_id,
        bool(item.get("completed")),
        bool(item.get("has_photo")),
        bool(item.get("requires_photo")),
    )

    await render(update, context, text, kb, message_id)
    return set_state(context, ITEM_DETAIL)


async def send_new_item_detail(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    item_id: int,
    notice: str | None = None,
) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU

    chat_id = update.effective_chat.id
    if not chat_id:
        return MAIN_MENU

    item = get_item_by_id(user.id, item_id)

    if not item:
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Задача не найдена."
        )
        return MAIN_MENU

    text = item_detail_text(item)

    if notice:
        text = f"{notice}\n\n{text}"

    kb = item_detail_keyboard(
        item_id,
        bool(item.get("completed")),
        bool(item.get("has_photo")),
        bool(item.get("requires_photo")),
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=kb,
    )

    return set_state(context, ITEM_DETAIL)


async def view_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data or ""

    await answer(query)

    user = update.effective_user
    if not user:
        return MAIN_MENU

    message_id = query.message.message_id if query.message else None

    if data.startswith(CB_ITEM_PREFIX):
        try:
            item_id = int(data.split(":", 1)[1])
        except (TypeError, ValueError):
            return await show_categories(update, context, message_id)

        return await show_item_detail(update, context, item_id, message_id)

    if data == CB_BACK_CATEGORIES:
        return await show_categories(update, context, message_id)

    if data == CB_BACK_MENU:
        return MAIN_MENU

    return await show_current_checklist(update, context, message_id)


async def show_photo_prompt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    item_id: int,
) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU

    chat_id = update.effective_chat.id
    if not chat_id:
        return MAIN_MENU

    item = get_item_by_id(user.id, item_id)

    if not item:
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Задача не найдена."
        )
        return MAIN_MENU

    text = (
        "📷 Отправьте одно или несколько фото/видео одним сообщением (альбомом).\n\n"
        f"Задача:\n{item.get('text')}\n\n"
        "После загрузки все файлы будут сохранены в служебный канал."
    )

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=photo_prompt_keyboard(False),
    )

    context.user_data["await_photo"] = {
        "item_id": item_id,
        "mark_done": not bool(item.get("completed")),
        "prompt_message_id": msg.message_id,
        "collected_files": [],  # для накопления файлов при альбоме
    }

    return set_state(context, AWAIT_TASK_PHOTO)


async def toggle_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data or ""

    user = update.effective_user
    if not user:
        return MAIN_MENU

    message_id = query.message.message_id if query.message else None

    # ---------- ОБРАБОТКА ПРОСТОГО ВЫПОЛНЕНИЯ (TOGGLE) ----------
    if data.startswith(CB_TOGGLE_PREFIX):
        try:
            item_id = int(data.split(":", 1)[1])
        except (TypeError, ValueError):
            await answer(query)
            return await show_current_checklist(update, context, message_id)

        # Проверяем, требует ли задача фото и ещё не выполнена
        item = get_item_by_id(user.id, item_id)
        if item and item.get("requires_photo") and not item.get("completed"):
            await answer(query, "Эта задача требует фото. Используйте кнопку 'Выполнить с фото'.", show_alert=True)
            return await show_item_detail(update, context, item_id, message_id)

        new_state = toggle_item(user.id, item_id)

        if new_state is None:
            await answer(query)
            return await show_current_checklist(update, context, message_id, notice="⚠️ Задача не найдена.")

        toast = "✅ Выполнено" if new_state else "↩️ Отменено"
        await answer(query, toast)

        return await show_item_detail(update, context, item_id, message_id)

    # ---------- ЗАПРОС НА ПРИКРЕПЛЕНИЕ ФОТО ----------
    if data.startswith(CB_PHOTO_PREFIX):
        try:
            item_id = int(data.split(":", 1)[1])
        except (TypeError, ValueError):
            await answer(query)
            return await show_current_checklist(update, context, message_id)

        item = get_item_by_id(user.id, item_id)

        if not item:
            await answer(query)
            return await show_current_checklist(update, context, message_id, notice="⚠️ Задача не найдена.")

        await answer(query)
        return await show_photo_prompt(update, context, item_id)

    # ---------- ПРОСМОТР ПРИКРЕПЛЁННЫХ ВЛОЖЕНИЙ ----------
    if data.startswith(CB_VIEW_PHOTO_PREFIX):
        try:
            item_id = int(data.split(":", 1)[1])
        except (TypeError, ValueError):
            await answer(query)
            return await show_current_checklist(update, context, message_id)

        item = get_item_by_id(user.id, item_id)
        logger.info(f"👁 Запрос просмотра вложений для задачи {item_id}")

        if not item or not item.get("media_items"):
            logger.warning(f"⚠️ Вложения не найдены для задачи {item_id}")
            await answer(query, "Вложения не найдены")
            return await show_item_detail(update, context, item_id, message_id)

        chat_id = update.effective_chat.id
        if chat_id:
            try:
                media_items = item.get("media_items", [])
                logger.info(f"📦 Количество вложений: {len(media_items)}")
                if len(media_items) > 10:
                    media_items = media_items[:10]
                    logger.info("✂️ Обрезано до 10 вложений")

                from telegram import InputMediaPhoto, InputMediaVideo
                media_group = []
                for i, media in enumerate(media_items):
                    # ✅ Исправлено: caption передаётся в конструктор
                    if media.get("type") == "photo":
                        media_obj = InputMediaPhoto(
                            media=media["file_id"],
                            caption="📸 Вложения к задаче" if i == 0 else None
                        )
                    elif media.get("type") == "video":
                        media_obj = InputMediaVideo(
                            media=media["file_id"],
                            caption="📸 Вложения к задаче" if i == 0 else None
                        )
                    else:
                        continue
                    media_group.append(media_obj)

                if media_group:
                    logger.info(f"📤 Отправка {len(media_group)} вложений пользователю")
                    await context.bot.send_media_group(chat_id=chat_id, media=media_group)
                    await answer(query, "Вложения отправлены выше")
                else:
                    await answer(query, "Нет подходящих вложений для отправки")
            except Exception as e:
                logger.error(f"❌ Ошибка отправки вложений: {e}")
                await answer(query, "Не удалось отправить вложения")
        else:
            await answer(query, "Не удалось отправить вложения")

        return set_state(context, ITEM_DETAIL)

    # ---------- КНОПКИ НАВИГАЦИИ ----------
    await answer(query)

    if data == CB_BACK_CATEGORIES:
        return await show_current_checklist(update, context, message_id)

    if data == CB_BACK_MENU:
        return MAIN_MENU

    return await show_current_checklist(update, context, message_id)


# ---------- ОБРАБОТКА ВХОДЯЩИХ ФОТО/ВИДЕО (ОДИНОЧНЫХ И АЛЬБОМОВ) ----------
def _extract_media_item(message) -> dict | None:
    """Извлекает информацию о медиа из сообщения."""
    if message.photo:
        return {"type": "photo", "file_id": message.photo[-1].file_id}
    elif message.video:
        return {"type": "video", "file_id": message.video.file_id}
    return None


def _is_album_message(message) -> bool:
    """Проверяет, является ли сообщение частью альбома."""
    return hasattr(message, 'media_group_id') and message.media_group_id is not None


async def _process_media_items(update: Update, context: ContextTypes.DEFAULT_TYPE,
                               meta: dict, items: list[dict]) -> int:
    """Обрабатывает список медиа-файлов (альбом или несколько)."""
    user = update.effective_user
    chat_id = update.effective_chat.id

    item_id = meta.get("item_id")
    mark_done = bool(meta.get("mark_done"))
    prompt_message_id = meta.get("prompt_message_id")

    logger.info(f"📥 Обработка медиа для задачи {item_id}, количество файлов: {len(items)}, mark_done={mark_done}")

    task_item = get_item_by_id(user.id, item_id)
    if not task_item:
        logger.warning(f"⚠️ Задача {item_id} не найдена")
        context.user_data.pop("await_photo", None)
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Задача не найдена.")
        return MAIN_MENU

    # Формируем подпись для альбома
    caption = build_photo_caption(user.id, task_item)

    # Отправляем альбом в канал
    try:
        message_ids = await send_media_group_to_channel(context, items, caption)
        logger.info(f"📨 Альбом отправлен в канал, message_ids: {message_ids}")
    except Exception as e:
        logger.error(f"❌ Не удалось отправить альбом в канал: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Не удалось загрузить альбом в канал. Попробуйте отправить файлы по одному."
        )
        return set_state(context, AWAIT_TASK_PHOTO)

    # Сохраняем все file_id и message_id
    attach_media_to_task(
        user_id=user.id,
        item_id=item_id,
        media_items=items,
        channel_message_ids=message_ids,
        mark_done=mark_done,
    )
    logger.info(f"💾 Медиа сохранены для задачи {item_id}")

    context.user_data.pop("await_photo", None)
    await cleanup_message(context, chat_id, prompt_message_id, "✅ Альбом получен")

    notice = "🎉 Молодец! Задача выполнена, альбом сохранён." if mark_done else "🎉 Молодец! Альбом сохранён."
    return await send_new_item_detail(update, context, item_id, notice)


async def _handle_single_media(update: Update, context: ContextTypes.DEFAULT_TYPE,
                               meta: dict) -> int:
    """Обрабатывает одиночное фото или видео."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    item_id = meta.get("item_id")
    mark_done = bool(meta.get("mark_done"))
    prompt_message_id = meta.get("prompt_message_id")

    logger.info(f"📥 Обработка одиночного медиа для задачи {item_id}, mark_done={mark_done}")

    task_item = get_item_by_id(user.id, item_id)
    if not task_item:
        logger.warning(f"⚠️ Задача {item_id} не найдена")
        context.user_data.pop("await_photo", None)
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Задача не найдена.")
        return MAIN_MENU

    # Определяем тип медиа
    media_item = _extract_media_item(update.message)
    if not media_item:
        logger.warning("⚠️ Не удалось распознать файл")
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Не удалось распознать файл. Отправьте фото или видео."
        )
        return set_state(context, AWAIT_TASK_PHOTO)

    # Отправляем одиночный файл в канал
    try:
        caption = build_photo_caption(user.id, task_item)
        message_id = await send_photo_to_channel(context, media_item["file_id"], caption)
        logger.info(f"📨 Одиночный файл отправлен в канал, message_id={message_id}")
    except Exception as e:
        logger.error(f"❌ Не удалось отправить файл в канал: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Не удалось загрузить файл в канал. Попробуйте ещё раз."
        )
        return set_state(context, AWAIT_TASK_PHOTO)

    # Сохраняем
    attach_media_to_task(
        user_id=user.id,
        item_id=item_id,
        media_items=[media_item],
        channel_message_ids=[message_id],
        mark_done=mark_done,
    )
    logger.info(f"💾 Медиа сохранено для задачи {item_id}")

    context.user_data.pop("await_photo", None)
    await cleanup_message(context, chat_id, prompt_message_id, "✅ Файл получен")

    notice = "🎉 Молодец! Задача выполнена, файл сохранён." if mark_done else "🎉 Молодец! Файл сохранён."
    return await send_new_item_detail(update, context, item_id, notice)


async def photo_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU

    chat_id = update.effective_chat.id
    if not chat_id:
        return MAIN_MENU

    meta = context.user_data.get("await_photo")
    if not meta:
        logger.warning("⚠️ Получено фото, но нет активного ожидания")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Начните заново с /start."
        )
        return MAIN_MENU

    # Проверяем, является ли сообщение частью альбома
    if _is_album_message(update.message):
        logger.info(f"📸 Обнаружен альбом, media_group_id={update.message.media_group_id}")
        return await _handle_album_part(update, context, meta)
    else:
        logger.info("📸 Получено одиночное медиа")
        return await _handle_single_media(update, context, meta)


async def _handle_album_part(update: Update, context: ContextTypes.DEFAULT_TYPE,
                             meta: dict) -> int:
    """Собирает все части альбома с задержкой."""
    global _album_buffer

    media_group_id = update.message.media_group_id
    if not media_group_id:
        return AWAIT_TASK_PHOTO

    if media_group_id not in _album_buffer:
        _album_buffer[media_group_id] = {
            "items": [],
            "meta": meta,
            "last_update": update,
            "timer_started": False,
        }
        logger.info(f"🔄 Начало сбора альбома {media_group_id}")

    # Добавляем текущий файл
    item = _extract_media_item(update.message)
    if item:
        _album_buffer[media_group_id]["items"].append(item)
        _album_buffer[media_group_id]["last_update"] = update
        logger.info(f"➕ Добавлен файл в альбом {media_group_id}, всего: {len(_album_buffer[media_group_id]['items'])}")

    # Если таймер ещё не запущен, запускаем его
    if not _album_buffer[media_group_id]["timer_started"]:
        _album_buffer[media_group_id]["timer_started"] = True
        asyncio.create_task(_process_album_after_delay(media_group_id, context))
        logger.info(f"⏳ Запущен таймер для альбома {media_group_id}")

    return AWAIT_TASK_PHOTO


async def _process_album_after_delay(media_group_id: str, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает собранный альбом после задержки."""
    global _album_buffer

    await asyncio.sleep(1.5)

    album_data = _album_buffer.pop(media_group_id, None)
    if not album_data:
        logger.warning(f"⚠️ Альбом {media_group_id} не найден в буфере")
        return

    items = album_data.get("items", [])
    if not items:
        logger.warning(f"⚠️ Альбом {media_group_id} пуст")
        return

    update = album_data.get("last_update")
    meta = album_data.get("meta")

    if not update or not meta:
        logger.warning(f"⚠️ Альбом {media_group_id} не имеет обновления или мета")
        return

    logger.info(f"📦 Альбом {media_group_id} собран, файлов: {len(items)}")

    try:
        await _process_media_items(update, context, meta, items)
    except Exception as e:
        logger.error(f"❌ Ошибка обработки альбома {media_group_id}: {e}")
        chat_id = update.effective_chat.id
        if chat_id:
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ Произошла ошибка при обработке альбома. Попробуйте отправить файлы по одному."
            )


async def photo_wrong_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id
    if chat_id:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "⚠️ Пожалуйста, отправьте именно фото или видео.\n\n"
                "Если хотите отменить прикрепление, нажмите кнопку «Отмена»."
            ),
        )
    return set_state(context, AWAIT_TASK_PHOTO)


async def photo_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await answer(query)

    user = update.effective_user
    if not user:
        return MAIN_MENU

    chat_id = update.effective_chat.id

    meta = context.user_data.get("await_photo") or {}
    item_id = meta.get("item_id")
    prompt_message_id = meta.get("prompt_message_id")

    if not prompt_message_id and query.message:
        prompt_message_id = query.message.message_id

    context.user_data.pop("await_photo", None)
    logger.info(f"❌ Отмена прикрепления фото для задачи {item_id}")

    await cleanup_message(context, chat_id, prompt_message_id, "❌ Отменено")

    if item_id:
        return await send_new_item_detail(update, context, item_id, notice="Отменено.")

    return MAIN_MENU


async def photo_state_guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await answer(query, "Сначала отправьте фото/видео или нажмите «Отмена»")
    return set_state(context, AWAIT_TASK_PHOTO)


async def show_progress(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
    notice: str | None = None,
) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU

    summary = get_user_progress_summary(user.id)

    if summary is None:
        await render(update, context, "Сначала начните смену.", None, message_id)
        return MAIN_MENU

    done, total, items, categories = summary

    if total == 0:
        text = "📊 Прогресс\n\nНа сегодня задач нет."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ В меню", callback_data=CB_BACK_MENU)]])
    else:
        bar = progress_bar(done, total)
        pct = percent(done, total)

        lines = [
            "📊 Прогресс",
            "",
            f"{bar} {done}/{total} · {pct}%",
            "",
        ]

        for cat, stats in categories.items():
            cat_label = CATEGORY_NAMES.get(cat, cat)
            lines.append(f"{cat_label} · {stats['done']}/{stats['total']}")

        if done == total:
            lines.append("")
            lines.append("🎉 Все задачи выполнены!")
        else:
            undone = [item for item in items if not item.get("completed")]
            lines.append("")
            lines.append(f"Осталось: {len(undone)}")

        text = "\n".join(lines)
        kb = progress_keyboard()

    if notice:
        text = f"{notice}\n\n{text}"

    await render(update, context, text, kb, message_id)
    return set_state(context, PROGRESS_VIEW)


async def progress_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await answer(query)

    message_id = query.message.message_id if query.message else None
    return MAIN_MENU


async def noop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await answer(query)
    return context.user_data.get("state", MAIN_MENU)