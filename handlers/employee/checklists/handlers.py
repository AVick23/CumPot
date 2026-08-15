import logging
import asyncio

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
    InputMediaVideo,
)
from telegram.ext import ContextTypes

from utils.channel import send_media_group_to_channel

from .utils import (
    set_state,
    current_state,
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
    CB_NOOP,
    CB_CATEGORY_PREFIX,
    CB_ITEM_PREFIX,
    CB_TOGGLE_PREFIX,
    CB_PHOTO_ADD_PREFIX,
    CB_PHOTO_REPLACE_PREFIX,
    CB_VIEW_PHOTO_PREFIX,
    CB_PHOTO_CANCEL,
    CB_BACK_MENU,
    CB_BACK_CATEGORIES,
    MEDIA_CHUNK_SIZE,
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

# Буфер для сборки альбомов
_album_buffer: dict[str, dict] = {}


# =========================================================
# CATEGORY SCREEN
# =========================================================

async def show_categories(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
    notice: str | None = None,
) -> int:
    user = update.effective_user

    if not user:
        return MAIN_MENU

    logger.info("📋 Пользователь %s открыл список категорий", user.id)

    items = get_checklist_items(user.id)

    if items is None:
        logger.info("⚠️ Пользователь %s пытается открыть чек-лист без активной смены", user.id)

        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("◀️ В меню", callback_data=CB_BACK_MENU)
                ]
            ]
        )

        await render(
            update,
            context,
            "Сначала начните смену.",
            kb,
            message_id,
        )

        return set_state(context, CATEGORY_SELECT)

    stats = get_categories_stats(user.id)

    if not stats:
        text = "📋 Чек-лист\n\nНа сегодня задач нет."

        if notice:
            text = f"{notice}\n\n{text}"

        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("◀️ В меню", callback_data=CB_BACK_MENU)
                ]
            ]
        )

        await render(update, context, text, kb, message_id)

        return set_state(context, CATEGORY_SELECT)

    text = "📋 Чек-лист\n\nВыберите раздел."

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

    logger.info("🔘 Пользователь нажал callback: %s", data)

    if data.startswith(CB_CATEGORY_PREFIX):
        category = data.split(":", 1)[1]

        logger.info("📂 Выбрана категория: %s", category)

        context.user_data["current_category"] = category

        return await show_checklist(update, context, category, message_id)

    if data == CB_BACK_MENU:
        logger.info("⬅️ Пользователь вернулся в меню из категорий")
        return MAIN_MENU

    return await show_categories(update, context, message_id)


# =========================================================
# CHECKLIST SCREEN
# =========================================================

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

    logger.info("📂 Пользователь %s открывает категорию %s", user.id, category)

    items = get_items_by_category(user.id, category)

    if items is None:
        await render(update, context, "Сначала начните смену.", None, message_id)
        return set_state(context, CATEGORY_SELECT)

    if not items:
        return await show_categories(
            update,
            context,
            message_id,
            notice="В этой категории нет задач.",
        )

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


# =========================================================
# ITEM DETAIL
# =========================================================

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

    logger.info("📌 Пользователь %s открывает задачу %s", user.id, item_id)

    item = get_item_by_id(user.id, item_id)

    if not item:
        logger.warning("⚠️ Задача %s не найдена для пользователя %s", item_id, user.id)

        return await show_current_checklist(
            update,
            context,
            message_id,
            notice="⚠️ Задача не найдена.",
        )

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
            text="⚠️ Задача не найдена.",
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

    logger.info("📌 Отправлена новая карточка задачи %s для пользователя %s", item_id, user.id)

    return set_state(context, ITEM_DETAIL)


async def view_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data or ""

    await answer(query)

    user = update.effective_user

    if not user:
        return MAIN_MENU

    message_id = query.message.message_id if query.message else None

    logger.info("🔘 Пользователь %s нажал callback: %s", user.id, data)

    if data.startswith(CB_ITEM_PREFIX):
        try:
            item_id = int(data.split(":", 1)[1])
        except (TypeError, ValueError):
            return await show_categories(update, context, message_id)

        return await show_item_detail(update, context, item_id, message_id)

    if data == CB_BACK_CATEGORIES:
        logger.info("⬅️ Пользователь %s вернулся к категориям", user.id)
        return await show_categories(update, context, message_id)

    if data == CB_BACK_MENU:
        logger.info("⬅️ Пользователь %s вернулся в меню", user.id)
        return MAIN_MENU

    return await show_current_checklist(update, context, message_id)


# =========================================================
# TOGGLE / PHOTO / VIEW PHOTO CALLBACK
# =========================================================

async def toggle_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data or ""

    user = update.effective_user

    if not user:
        return MAIN_MENU

    message_id = query.message.message_id if query.message else None

    logger.info("🔘 Пользователь %s нажал callback: %s", user.id, data)

    # Простое выполнение / отмена
    if data.startswith(CB_TOGGLE_PREFIX):
        try:
            item_id = int(data.split(":", 1)[1])
        except (TypeError, ValueError):
            await answer(query)
            return await show_current_checklist(update, context, message_id)

        item = get_item_by_id(user.id, item_id)

        if item and item.get("requires_photo") and not item.get("completed"):
            logger.info(
                "⚠️ Пользователь %s попытался выполнить задачу %s без фото",
                user.id,
                item_id,
            )

            await answer(
                query,
                "Эта задача требует фото. Используйте кнопку «📸 Выполнить с фото».",
                show_alert=True,
            )

            return await show_item_detail(update, context, item_id, message_id)

        new_state = toggle_item(user.id, item_id)

        if new_state is None:
            await answer(query)

            return await show_current_checklist(
                update,
                context,
                message_id,
                notice="⚠️ Задача не найдена.",
            )

        toast = "✅ Выполнено" if new_state else "↩️ Отменено"

        logger.info(
            "%s задача %s пользователем %s",
            "✅ Выполнена" if new_state else "↩️ Отменена",
            item_id,
            user.id,
        )

        await answer(query, toast)

        return await show_item_detail(update, context, item_id, message_id)

    # Обработка добавления/замены фото
    if data.startswith(CB_PHOTO_ADD_PREFIX) or data.startswith(CB_PHOTO_REPLACE_PREFIX):
        try:
            # Формат: prefix + item_id
            item_id = int(data.split(":", 1)[1])
        except (TypeError, ValueError):
            await answer(query)
            return await show_current_checklist(update, context, message_id)

        item = get_item_by_id(user.id, item_id)

        if not item:
            await answer(query)
            return await show_current_checklist(
                update,
                context,
                message_id,
                notice="⚠️ Задача не найдена.",
            )

        # Определяем действие
        if data.startswith(CB_PHOTO_REPLACE_PREFIX):
            replace_action = True
            toast = "Вы выбрали замену фото"
        else:
            replace_action = False
            toast = "Вы выбрали добавление фото"

        # Сохраняем действие в context
        context.user_data["photo_replace"] = replace_action

        await answer(query, toast)

        logger.info(
            "📸 Пользователь %s запросил %s фото к задаче %s",
            user.id,
            "замену" if replace_action else "добавление",
            item_id,
        )

        return await show_photo_prompt(update, context, item_id)

    # Просмотр фото
    if data.startswith(CB_VIEW_PHOTO_PREFIX):
        try:
            item_id = int(data.split(":", 1)[1])
        except (TypeError, ValueError):
            await answer(query)
            return await show_current_checklist(update, context, message_id)

        item = get_item_by_id(user.id, item_id)

        if not item or not item.get("media_items"):
            await answer(query, "Вложения не найдены")

            return await show_item_detail(update, context, item_id, message_id)

        chat_id = update.effective_chat.id

        if not chat_id:
            await answer(query, "Не удалось отправить вложения")
            return set_state(context, ITEM_DETAIL)

        await answer(query, "Отправляю вложения...")

        caption = f"📸 Вложения к задаче\n\n{item.get('text')}"

        sent = await _send_media_to_chat(
            context,
            chat_id,
            item.get("media_items", []),
            caption=caption,
        )

        if sent:
            logger.info(
                "👁 Пользователь %s получил вложения по задаче %s",
                user.id,
                item_id,
            )
            return set_state(context, ITEM_DETAIL)

        return await show_item_detail(
            update,
            context,
            item_id,
            message_id,
            notice="⚠️ Не удалось отправить вложения.",
        )

    await answer(query)

    if data == CB_BACK_CATEGORIES:
        logger.info("⬅️ Пользователь %s вернулся к списку задач", user.id)
        return await show_current_checklist(update, context, message_id)

    if data == CB_BACK_MENU:
        logger.info("⬅️ Пользователь %s вернулся в меню", user.id)
        return MAIN_MENU

    if data == CB_NOOP:
        return current_state(context)

    return await show_current_checklist(update, context, message_id)


# =========================================================
# PHOTO PROMPT
# =========================================================

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
            text="⚠️ Задача не найдена.",
        )

        return MAIN_MENU

    logger.info("📸 Пользователь %s открывает окно загрузки фото для задачи %s", user.id, item_id)

    text = (
        "📸 Прикрепите фото к задаче\n\n"
        f"📌 {item.get('text')}\n\n"
        "Отправьте фото или видео одним сообщением.\n"
        "Можно отправить несколько файлов альбомом."
    )

    if item.get("requires_photo"):
        text += "\n\n⚠️ Без фото эта задача не может быть выполнена."

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=photo_prompt_keyboard(bool(item.get("has_photo"))),
    )

    context.user_data["await_photo"] = {
        "item_id": item_id,
        "mark_done": not bool(item.get("completed")),
        "prompt_message_id": msg.message_id,
        "replace": context.user_data.get("photo_replace", False),  # сохраняем действие
    }

    return set_state(context, AWAIT_TASK_PHOTO)


# =========================================================
# PHOTO INPUT
# =========================================================

def _extract_media_item(message) -> dict | None:
    if message.photo:
        return {
            "type": "photo",
            "file_id": message.photo[-1].file_id,
        }

    if message.video:
        return {
            "type": "video",
            "file_id": message.video.file_id,
        }

    return None


def _is_album_message(message) -> bool:
    return hasattr(message, "media_group_id") and message.media_group_id is not None


async def photo_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user

    if not user:
        return MAIN_MENU

    chat_id = update.effective_chat.id

    if not chat_id:
        return MAIN_MENU

    meta = context.user_data.get("await_photo")

    if not meta:
        logger.warning("⚠️ Получено медиа, но нет активного ожидания фото")

        await context.bot.send_message(
            chat_id=chat_id,
            text="Начните заново с /start.",
        )

        return MAIN_MENU

    if _is_album_message(update.message):
        logger.info(
            "📸 Пользователь %s отправил часть альбома media_group_id=%s",
            user.id,
            update.message.media_group_id,
        )

        return await _handle_album_part(update, context, meta)

    logger.info("📸 Пользователь %s отправил одиночное медиа", user.id)

    return await _handle_single_media(update, context, meta)


async def _handle_album_part(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    meta: dict,
) -> int:
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

        logger.info("🔄 Начинаю сбор альбома %s", media_group_id)

    media_item = _extract_media_item(update.message)

    if media_item:
        _album_buffer[media_group_id]["items"].append(media_item)
        _album_buffer[media_group_id]["last_update"] = update

        logger.info(
            "➕ Добавлен файл в альбом %s. Всего файлов: %s",
            media_group_id,
            len(_album_buffer[media_group_id]["items"]),
        )

    if not _album_buffer[media_group_id]["timer_started"]:
        _album_buffer[media_group_id]["timer_started"] = True

        asyncio.create_task(
            _process_album_after_delay(media_group_id, context)
        )

        logger.info("⏳ Запущен таймер обработки альбома %s", media_group_id)

    return AWAIT_TASK_PHOTO


async def _process_album_after_delay(
    media_group_id: str,
    context: ContextTypes.DEFAULT_TYPE,
):
    global _album_buffer

    await asyncio.sleep(1.5)

    album_data = _album_buffer.pop(media_group_id, None)

    if not album_data:
        logger.warning("⚠️ Альбом %s не найден в буфере", media_group_id)
        return

    items = album_data.get("items", [])

    if not items:
        logger.warning("⚠️ Альбом %s оказался пустым", media_group_id)
        return

    update = album_data.get("last_update")
    meta = album_data.get("meta")

    if not update or not meta:
        logger.warning("⚠️ Альбом %s не имеет update или meta", media_group_id)
        return

    logger.info("📦 Альбом %s собран. Файлов: %s", media_group_id, len(items))

    try:
        await _process_media_items(update, context, meta, items)
    except Exception as e:
        logger.error("❌ Ошибка обработки альбома %s: %s", media_group_id, e, exc_info=True)

        chat_id = update.effective_chat.id

        if chat_id:
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ Произошла ошибка при обработке альбома. Попробуйте отправить файлы по одному.",
            )


async def _process_media_items(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    meta: dict,
    items: list[dict],
) -> int:
    user = update.effective_user

    if not user:
        return MAIN_MENU

    chat_id = update.effective_chat.id

    if not chat_id:
        return MAIN_MENU

    item_id = meta.get("item_id")
    mark_done = bool(meta.get("mark_done"))
    prompt_message_id = meta.get("prompt_message_id")
    replace = bool(meta.get("replace", False))  # извлекаем действие

    logger.info(
        "📥 Обрабатываю медиа для задачи %s. Файлов: %s. mark_done=%s, replace=%s",
        item_id,
        len(items),
        mark_done,
        replace,
    )

    task_item = get_item_by_id(user.id, item_id)

    if not task_item:
        logger.warning("⚠️ Задача %s не найдена при обработке медиа", item_id)

        context.user_data.pop("await_photo", None)

        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Задача не найдена.",
        )

        return MAIN_MENU

    caption = build_photo_caption(user.id, task_item)

    try:
        channel_message_ids = await send_media_group_to_channel(
            context,
            items,
            caption,
        )

        logger.info("📨 Медиа отправлены в канал. message_ids=%s", channel_message_ids)

    except Exception as e:
        logger.error("❌ Не удалось отправить медиа в канал: %s", e, exc_info=True)

        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Не удалось загрузить файлы в канал. Попробуйте отправить их по одному.",
        )

        return set_state(context, AWAIT_TASK_PHOTO)

    attach_media_to_task(
        user_id=user.id,
        item_id=item_id,
        media_items=items,
        channel_message_ids=channel_message_ids,
        mark_done=mark_done,
        task_item=task_item,
        replace=replace,
    )

    context.user_data.pop("await_photo", None)
    context.user_data.pop("photo_replace", None)  # очищаем

    await cleanup_message(context, chat_id, prompt_message_id, "✅ Файлы получены")

    notice = (
        "🎉 Молодец! Задача выполнена, фото сохранены."
        if mark_done
        else "🎉 Молодец! Фото сохранены."
    )

    logger.info("✅ Медиа привязаны к задаче %s пользователем %s", item_id, user.id)

    return await send_new_item_detail(update, context, item_id, notice)


async def _handle_single_media(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    meta: dict,
) -> int:
    user = update.effective_user

    if not user:
        return MAIN_MENU

    chat_id = update.effective_chat.id

    if not chat_id:
        return MAIN_MENU

    item_id = meta.get("item_id")
    mark_done = bool(meta.get("mark_done"))
    prompt_message_id = meta.get("prompt_message_id")
    replace = bool(meta.get("replace", False))

    logger.info(
        "📥 Обрабатываю одиночное медиа для задачи %s. mark_done=%s, replace=%s",
        item_id,
        mark_done,
        replace,
    )

    task_item = get_item_by_id(user.id, item_id)

    if not task_item:
        logger.warning("⚠️ Задача %s не найдена при обработке одиночного медиа", item_id)

        context.user_data.pop("await_photo", None)

        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Задача не найдена.",
        )

        return MAIN_MENU

    media_item = _extract_media_item(update.message)

    if not media_item:
        logger.warning("⚠️ Не удалось распознать файл от пользователя %s", user.id)

        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Не удалось распознать файл. Отправьте фото или видео.",
        )

        return set_state(context, AWAIT_TASK_PHOTO)

    caption = build_photo_caption(user.id, task_item)

    try:
        channel_message_ids = await send_media_group_to_channel(
            context,
            [media_item],
            caption,
        )

        logger.info("📨 Одиночный файл отправлен в канал. message_ids=%s", channel_message_ids)

    except Exception as e:
        logger.error("❌ Не удалось отправить одиночный файл в канал: %s", e, exc_info=True)

        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Не удалось загрузить файл в канал. Попробуйте ещё раз.",
        )

        return set_state(context, AWAIT_TASK_PHOTO)

    attach_media_to_task(
        user_id=user.id,
        item_id=item_id,
        media_items=[media_item],
        channel_message_ids=channel_message_ids,
        mark_done=mark_done,
        task_item=task_item,
        replace=replace,
    )

    context.user_data.pop("await_photo", None)
    context.user_data.pop("photo_replace", None)

    await cleanup_message(context, chat_id, prompt_message_id, "✅ Файл получен")

    notice = (
        "🎉 Молодец! Задача выполнена, фото сохранены."
        if mark_done
        else "🎉 Молодец! Фото сохранены."
    )

    logger.info("✅ Одиночный файл привязан к задаче %s пользователем %s", item_id, user.id)

    return await send_new_item_detail(update, context, item_id, notice)


async def photo_wrong_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id

    logger.warning("⚠️ Пользователь отправил неподдерживаемый тип файла")

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
    context.user_data.pop("photo_replace", None)

    logger.info("❌ Пользователь %s отменил прикрепление фото к задаче %s", user.id, item_id)

    await cleanup_message(context, chat_id, prompt_message_id, "❌ Отменено")

    if item_id:
        return await send_new_item_detail(update, context, item_id, notice="Отменено.")

    return MAIN_MENU


async def photo_state_guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    await answer(
        query,
        "Сначала отправьте фото/видео или нажмите «Отмена»",
        show_alert=True,
    )

    return set_state(context, AWAIT_TASK_PHOTO)


# =========================================================
# PROGRESS
# =========================================================

async def show_progress(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    message_id: int | None = None,
    notice: str | None = None,
) -> int:
    user = update.effective_user

    if not user:
        return MAIN_MENU

    logger.info("📊 Пользователь %s открыл прогресс", user.id)

    summary = get_user_progress_summary(user.id)

    if summary is None:
        await render(update, context, "Сначала начните смену.", None, message_id)
        return MAIN_MENU

    done, total, items, categories = summary

    if total == 0:
        text = "📊 Прогресс\n\nНа сегодня задач нет."

        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("◀️ В меню", callback_data=CB_BACK_MENU)
                ]
            ]
        )
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

    user = update.effective_user

    if user:
        logger.info("⬅️ Пользователь %s вернулся в меню из прогресса", user.id)

    return MAIN_MENU


async def noop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query

    await answer(query)

    return current_state(context)


# =========================================================
# MEDIA SEND HELPER
# =========================================================

async def _send_media_to_chat(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    media_items: list[dict],
    caption: str | None = None,
) -> bool:
    if not media_items:
        return False

    try:
        for start in range(0, len(media_items), MEDIA_CHUNK_SIZE):
            chunk = media_items[start:start + MEDIA_CHUNK_SIZE]
            media_group = []

            for index, media in enumerate(chunk):
                file_id = media.get("file_id")

                if not file_id:
                    continue

                media_caption = caption if start == 0 and index == 0 else None

                if media.get("type") == "video":
                    media_group.append(
                        InputMediaVideo(
                            media=file_id,
                            caption=media_caption,
                        )
                    )
                else:
                    media_group.append(
                        InputMediaPhoto(
                            media=file_id,
                            caption=media_caption,
                        )
                    )

            if media_group:
                await context.bot.send_media_group(
                    chat_id=chat_id,
                    media=media_group,
                )

        return True

    except Exception as e:
        logger.error("❌ Ошибка отправки медиа пользователю: %s", e, exc_info=True)
        return False