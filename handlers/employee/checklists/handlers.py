import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from utils.channel import send_photo_to_channel
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
    attach_photo_to_task,
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
)
from .keyboards import (
    categories_keyboard,
    checklist_keyboard,
    item_detail_keyboard,
    progress_keyboard,
    photo_prompt_keyboard,
)

# MAIN_MENU = 3 (совпадает с menu/constants.py)
MAIN_MENU = 3

logger = logging.getLogger(__name__)


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
        "📷 Отправьте фото одним сообщением.\n\n"
        f"Задача:\n{item.get('text')}\n\n"
        "После загрузки фото будет сохранено в служебный канал."
    )

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=photo_prompt_keyboard(),
    )

    context.user_data["await_photo"] = {
        "item_id": item_id,
        "mark_done": not bool(item.get("completed")),
        "prompt_message_id": msg.message_id,
    }

    return set_state(context, AWAIT_TASK_PHOTO)


async def toggle_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data or ""

    user = update.effective_user
    if not user:
        return MAIN_MENU

    message_id = query.message.message_id if query.message else None

    if data.startswith(CB_TOGGLE_PREFIX):
        try:
            item_id = int(data.split(":", 1)[1])
        except (TypeError, ValueError):
            await answer(query)
            return await show_current_checklist(update, context, message_id)

        new_state = toggle_item(user.id, item_id)

        if new_state is None:
            await answer(query)
            return await show_current_checklist(update, context, message_id, notice="⚠️ Задача не найдена.")

        toast = "✅ Выполнено" if new_state else "↩️ Отменено"
        await answer(query, toast)

        return await show_item_detail(update, context, item_id, message_id)

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

    if data.startswith(CB_VIEW_PHOTO_PREFIX):
        try:
            item_id = int(data.split(":", 1)[1])
        except (TypeError, ValueError):
            await answer(query)
            return await show_current_checklist(update, context, message_id)

        item = get_item_by_id(user.id, item_id)

        if not item or not item.get("photo_file_id"):
            await answer(query, "Фото не найдено")
            return await show_item_detail(update, context, item_id, message_id)

        chat_id = update.effective_chat.id

        if chat_id:
            try:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=item["photo_file_id"],
                )
                await answer(query, "Фото отправлено выше")
            except Exception as e:
                logger.warning("View photo failed: %s", e)
                await answer(query, "Не удалось отправить фото")
        else:
            await answer(query, "Не удалось отправить фото")

        return set_state(context, ITEM_DETAIL)

    await answer(query)

    if data == CB_BACK_CATEGORIES:
        return await show_current_checklist(update, context, message_id)

    if data == CB_BACK_MENU:
        return MAIN_MENU

    return await show_current_checklist(update, context, message_id)


async def photo_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if not user:
        return MAIN_MENU

    chat_id = update.effective_chat.id
    if not chat_id:
        return MAIN_MENU

    meta = context.user_data.get("await_photo")

    if not meta:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Начните заново с /start."
        )
        return MAIN_MENU

    if not update.message or not update.message.photo:
        return await photo_wrong_type(update, context)

    item_id = meta.get("item_id")
    mark_done = bool(meta.get("mark_done"))
    prompt_message_id = meta.get("prompt_message_id")

    item = get_item_by_id(user.id, item_id)

    if not item:
        context.user_data.pop("await_photo", None)
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Задача не найдена."
        )
        return MAIN_MENU

    photo_file_id = update.message.photo[-1].file_id
    caption = build_photo_caption(user.id, item)

    try:
        channel_message_id = await send_photo_to_channel(context, photo_file_id, caption)
    except Exception as e:
        logger.error("Failed to send photo to channel: %s", e)
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "⚠️ Не удалось загрузить фото в канал.\n\n"
                "Проверьте, что бот добавлен в канал администратором и имеет право публикации сообщений.\n\n"
                "Попробуйте отправить фото ещё раз."
            ),
        )
        return set_state(context, AWAIT_TASK_PHOTO)

    attach_photo_to_task(
        user_id=user.id,
        item_id=item_id,
        file_id=photo_file_id,
        channel_message_id=channel_message_id,
        mark_done=mark_done,
    )

    context.user_data.pop("await_photo", None)

    await cleanup_message(context, chat_id, prompt_message_id, "✅ Фото получено")

    if mark_done:
        notice = "🎉 Молодец! Задача выполнена, фото сохранено."
    else:
        notice = "🎉 Молодец! Фото сохранено."

    return await send_new_item_detail(update, context, item_id, notice)


async def photo_wrong_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id

    if chat_id:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "⚠️ Пожалуйста, отправьте именно фото.\n\n"
                "Если хотите отменить прикрепление фото, нажмите кнопку «Отмена» под запросом фото."
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

    await cleanup_message(context, chat_id, prompt_message_id, "❌ Отменено")

    if item_id:
        return await send_new_item_detail(update, context, item_id, notice="Отменено.")

    return MAIN_MENU


async def photo_state_guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await answer(query, "Сначала отправьте фото или нажмите «Отмена»")
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
    # ИСПРАВЛЕНИЕ: используем "state" вместо "employee_state"
    return context.user_data.get("state", MAIN_MENU)