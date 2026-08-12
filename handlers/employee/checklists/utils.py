import logging
from telegram.error import BadRequest
from utils.time_utils import today_msk_str, time_msk_str
from db.users import get_user
from db.shifts import get_active_shift
from db.checklist import (
    get_items_for_location_and_day,
    save_progress,
    get_progress_for_user_date,
    save_progress_photo,
    get_photos_for_user_date,
)
from .constants import CATEGORY_NAMES, CATEGORY_ORDER, MSG_LIMIT

logger = logging.getLogger(__name__)


# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С СОСТОЯНИЯМИ ----------
def set_state(context, state):
    context.user_data["employee_state"] = state
    return state


def current_state(context):
    return context.user_data.get("employee_state", 3)  # MAIN_MENU


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


# ---------- РАБОТА С ЧЕК-ЛИСТАМИ ----------
def get_checklist_items(user_id):
    shift = get_active_shift(user_id)
    if not shift:
        return None
    location = shift["location"]
    day_of_week = now_msk().weekday()  # нужно импортировать now_msk
    date_str = today_msk_str()
    items = get_items_for_location_and_day(location, day_of_week)
    if not items:
        return []
    progress = get_progress_for_user_date(user_id, date_str)
    progress_dict = {p["item_id"]: p["completed"] for p in progress}
    photos = get_photos_for_user_date(user_id, date_str)
    result = []
    for item in items:
        item = dict(item)
        item["completed"] = progress_dict.get(item["id"], 0) == 1
        photo = photos.get(item["id"])
        item["has_photo"] = bool(photo)
        item["photo_file_id"] = photo["file_id"] if photo else None
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
    item = get_item_by_id(user_id, item_id)
    if item is None:
        return None
    new_state = not bool(item.get("completed"))
    save_progress(user_id, item_id, new_state)
    return new_state


def attach_photo_to_task(user_id, item_id, file_id, channel_message_id, mark_done=False):
    if mark_done:
        save_progress(user_id, item_id, True)
    save_progress_photo(user_id, item_id, file_id, channel_message_id)


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
    photo_text = "🖼 Фото прикреплено" if item.get("has_photo") else "🖼 Фото: нет"

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
        from .constants import LOCATIONS  # импортируем локально, чтобы избежать цикла
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


# Чтобы использовать now_msk, импортируем из time_utils
from utils.time_utils import now_msk