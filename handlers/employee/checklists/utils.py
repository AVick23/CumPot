import logging
import json
import asyncio
from telegram.error import BadRequest
from utils.time_utils import today_msk_str, time_msk_str, now_msk
from db.users import get_user
from db.shifts import get_active_shift
from db.checklist import (
    get_items_for_location_and_day,
    get_shared_progress,
    save_shared_progress,
    save_shared_photo,  # оставлено для обратной совместимости
)
from .constants import CATEGORY_NAMES, CATEGORY_ORDER, MSG_LIMIT, LOCATIONS

logger = logging.getLogger(__name__)

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------
def set_state(context, state):
    context.user_data["state"] = state
    return state


def current_state(context):
    return context.user_data.get("state", 3)


def truncate_text(text, limit=MSG_LIMIT):
    text = text or ""
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + "…"


async def answer(query, text=None, show_alert=False):
    try:
        await query.answer(text or "", show_alert=show_alert)
    except Exception:
        pass


async def render(update, context, text, reply_markup=None, message_id=None):
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


# ---------- РАБОТА С ЧЕК-ЛИСТАМИ (ОБЩИЙ ПРОГРЕСС) ----------
def get_checklist_items(user_id):
    shift = get_active_shift(user_id)
    if not shift:
        return None
    location = shift["location"]
    date = today_msk_str()

    items = get_items_for_location_and_day(location, date)
    if not items:
        return []

    shared_progress = get_shared_progress(location, date)
    logger.info(f"get_checklist_items: shared_progress keys: {list(shared_progress.keys())}")

    result = []
    for item in items:
        item = dict(item)
        progress = shared_progress.get(item["id"])
        item["completed"] = progress.get("completed", 0) == 1 if progress else False

        media_items = []
        if progress:
            raw = progress.get("photo_file_ids")
            logger.info(f"item {item['id']}: raw photo_file_ids = {raw}")
            if raw:
                try:
                    media_items = json.loads(raw)
                    logger.info(f"item {item['id']}: parsed media_items = {media_items}")
                    if media_items and isinstance(media_items[0], str):
                        media_items = [{"type": "photo", "file_id": f} for f in media_items]
                        logger.info(f"item {item['id']}: converted to objects")
                except Exception as e:
                    logger.warning(f"item {item['id']}: failed to parse photo_file_ids: {e}")
                    media_items = []
            elif progress.get("photo_file_id"):
                media_items = [{"type": "photo", "file_id": progress["photo_file_id"]}]
                logger.info(f"item {item['id']}: using old photo_file_id")
        else:
            logger.info(f"item {item['id']}: no progress")

        item["media_items"] = media_items
        item["has_photo"] = bool(media_items)
        item["photo_count"] = len(media_items)
        if media_items:
            item["photo_file_id"] = media_items[0]["file_id"]
        else:
            item["photo_file_id"] = None

        result.append(item)
    return result


def get_categories_stats(user_id):
    items = get_checklist_items(user_id)
    if items is None:
        return None
    stats = {}
    for item in items:
        cat = item.get("category") or "weekly"
        stats.setdefault(cat, {"done": 0, "total": 0})
        stats[cat]["total"] += 1
        if item.get("completed"):
            stats[cat]["done"] += 1
    return stats


def get_items_by_category(user_id, category):
    items = get_checklist_items(user_id)
    if items is None:
        return None
    return [item for item in items if item.get("category") == category]


def get_item_by_id(user_id, item_id):
    items = get_checklist_items(user_id)
    if items is None:
        return None
    for item in items:
        if item["id"] == item_id:
            return item
    return None


def toggle_item(user_id, item_id):
    shift = get_active_shift(user_id)
    if not shift:
        return None
    location = shift["location"]
    date = today_msk_str()

    shared_progress = get_shared_progress(location, date)
    progress = shared_progress.get(item_id)
    current_state = progress.get("completed", 0) == 1 if progress else False
    new_state = not current_state

    save_shared_progress(location, date, item_id, new_state, user_id)
    return new_state


def attach_media_to_task(user_id, item_id, media_items: list, channel_message_ids: list, mark_done=False):
    logger.info(f"attach_media_to_task: user_id={user_id}, item_id={item_id}, media_items={media_items}, channel_message_ids={channel_message_ids}")
    shift = get_active_shift(user_id)
    if not shift:
        logger.warning("Нет активной смены, пропускаем сохранение")
        return
    location = shift["location"]
    date = today_msk_str()

    if mark_done:
        save_shared_progress(location, date, item_id, True, user_id)

    from db import get_connection
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM checklist_shared_progress WHERE location = ? AND date = ? AND item_id = ?",
            (location, date, item_id)
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE checklist_shared_progress
                SET photo_file_ids = ?, photo_channel_message_ids = ?, photo_file_id = NULL
                WHERE id = ?
                """,
                (json.dumps(media_items), json.dumps(channel_message_ids), existing["id"])
            )
            logger.info(f"Обновлена запись прогресса id={existing['id']}")
        else:
            conn.execute(
                """
                INSERT INTO checklist_shared_progress
                (location, date, item_id, completed, completed_by, photo_file_ids, photo_channel_message_ids, photo_file_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (location, date, item_id, 1 if mark_done else 0, user_id,
                 json.dumps(media_items), json.dumps(channel_message_ids))
            )
            logger.info("Создана новая запись прогресса")
        conn.commit()


# Для обратной совместимости (одиночное фото)
def attach_photo_to_task(user_id, item_id, file_id, channel_message_id, mark_done=False):
    attach_media_to_task(user_id, item_id, [{"type": "photo", "file_id": file_id}], [channel_message_id], mark_done)


def get_user_progress_summary(user_id):
    items = get_checklist_items(user_id)
    if items is None:
        return None
    total = len(items)
    done = sum(1 for item in items if item.get("completed"))
    categories = {}
    for item in items:
        cat = item.get("category") or "weekly"
        categories.setdefault(cat, {"done": 0, "total": 0})
        categories[cat]["total"] += 1
        if item.get("completed"):
            categories[cat]["done"] += 1
    ordered = {cat: categories[cat] for cat in CATEGORY_ORDER if cat in categories}
    return done, total, items, ordered


def progress_bar(done, total, size=10):
    if total <= 0:
        return "▱" * size
    filled = round(size * done / total)
    filled = max(0, min(size, filled))
    return "▰" * filled + "▱" * (size - filled)


def percent(done, total):
    return int(done / total * 100) if total else 0


# ---------- UI ПОМОЩНИКИ ----------
def item_detail_text(item: dict) -> str:
    status_text = "✅ Выполнено" if item.get("completed") else "⚪️ Не выполнено"
    category_label = CATEGORY_NAMES.get(item.get("category"), item.get("category"))
    photo_count = item.get("photo_count", 0)
    photo_text = f"🖼 Вложений: {photo_count} шт." if photo_count else "🖼 Вложений: нет"
    return (
        "📌 Задача\n\n"
        f"{item.get('text')}\n\n"
        f"Статус: {status_text}\n"
        f"Категория: {category_label}\n"
        f"{photo_text}"
    )


def build_photo_caption(user_id: int, item: dict) -> str:
    user_db = get_user(user_id)
    full_name = "Сотрудник"
    position_label = "—"
    if user_db:
        full_name = user_db.get("full_name") or "Сотрудник"
        position = user_db.get("position")
        position_label = LOCATIONS.get(position, position or "—")
    today = today_msk_str()
    now_time = time_msk_str()
    caption = (
        "📷 Фото к задаче\n\n"
        f"👤 {full_name}\n"
        f"📍 {position_label}\n"
        f"📅 {today}\n"
        f"🕒 {now_time}\n\n"
        f"Задача:\n{item.get('text')}"
    )
    if len(caption) > 1000:
        caption = caption[:1000] + "…"
    return caption