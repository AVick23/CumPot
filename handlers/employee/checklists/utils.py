import logging
import json

from telegram.error import BadRequest

from utils.time_utils import (
    today_msk_str,
    time_msk_str,
)

from db import get_connection
from db.users import get_user
from db.shifts import get_active_shift
from db.checklist import (
    get_items_for_location_and_day,
    get_shared_progress,
    save_shared_progress,
)

from .constants import (
    CATEGORY_NAMES,
    CATEGORY_ORDER,
    LOCATIONS,
    MSG_LIMIT,
)

logger = logging.getLogger(__name__)


# =========================================================
# STATE / UI HELPERS
# =========================================================

def set_state(context, state: int) -> int:
    context.user_data["state"] = state
    return state


def current_state(context) -> int:
    return context.user_data.get("state", 3)


def truncate_text(text: str | None, limit: int = MSG_LIMIT) -> str:
    text = text or ""

    if len(text) <= limit:
        return text

    return text[: limit - 1].rstrip() + "…"


async def answer(query, text: str | None = None, show_alert: bool = False):
    try:
        await query.answer(text or "", show_alert=show_alert)
    except Exception as e:
        logger.warning("Не удалось ответить на callback: %s", e)


async def render(update, context, text: str, reply_markup=None, message_id=None):
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


async def cleanup_message(context, chat_id, message_id, fallback_text: str = "✅ Готово"):
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


def progress_bar(done: int, total: int, size: int = 10) -> str:
    if total <= 0:
        return "▱" * size

    filled = round(size * done / total)
    filled = max(0, min(size, filled))

    return "▰" * filled + "▱" * (size - filled)


def percent(done: int, total: int) -> int:
    if total <= 0:
        return 0

    return int(done / total * 100)


def full_name(user: dict | None) -> str:
    if not user:
        return "Сотрудник"

    full = (user.get("full_name") or "").strip()
    if full:
        return full

    first = (user.get("first_name") or "").strip()
    last = (user.get("last_name") or "").strip()

    name = " ".join([x for x in [first, last] if x]).strip()
    if name:
        return name

    username = (user.get("username") or "").strip()
    if username:
        return f"@{username}"

    return str(user.get("tg_id", "Сотрудник"))


# =========================================================
# MEDIA HELPERS
# =========================================================

def _normalize_media_items(media_items: list) -> list[dict]:
    """
    Приводит медиа к единому формату:
    [
        {"type": "photo", "file_id": "..."},
        {"type": "video", "file_id": "..."},
    ]
    """
    result = []

    for item in media_items or []:
        if isinstance(item, str):
            if item.strip():
                result.append(
                    {
                        "type": "photo",
                        "file_id": item.strip(),
                    }
                )
            continue

        if isinstance(item, dict):
            file_id = item.get("file_id")

            if not file_id:
                continue

            result.append(
                {
                    "type": item.get("type", "photo"),
                    "file_id": file_id,
                }
            )

    return result


def _parse_media_raw(raw) -> list[dict]:
    """
    Парсит photo_file_ids из БД.

    Поддерживает:
    - JSON-массив строк
    - JSON-массив объектов
    - старый одиночный photo_file_id
    """
    if not raw:
        return []

    data = raw

    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception as e:
            logger.warning("Не удалось разобрать photo_file_ids: %s", e)
            return []

    if isinstance(data, dict):
        data = [data]

    if isinstance(data, str):
        data = [data]

    if not isinstance(data, list):
        return []

    result = []

    for entry in data:
        if isinstance(entry, str):
            if entry.strip():
                result.append(
                    {
                        "type": "photo",
                        "file_id": entry.strip(),
                    }
                )
            continue

        if isinstance(entry, dict):
            file_id = entry.get("file_id")

            if not file_id:
                continue

            media_item = dict(entry)
            media_item.setdefault("type", "photo")
            result.append(media_item)

    return result


# =========================================================
# CHECKLIST DATA
# =========================================================

def get_checklist_items(user_id: int) -> list[dict] | None:
    shift = get_active_shift(user_id)

    if not shift:
        logger.info("⚠️ get_checklist_items: нет активной смены у пользователя %s", user_id)
        return None

    location = shift.get("location")
    date = today_msk_str()

    items = get_items_for_location_and_day(location, date)

    if not items:
        logger.info("📋 get_checklist_items: задач нет для %s / %s", location, date)
        return []

    shared_progress = get_shared_progress(location, date)

    result = []

    for item in items:
        item = dict(item)

        progress = shared_progress.get(item.get("id"))

        completed = False
        media_items = []

        if progress:
            completed = progress.get("completed", 0) == 1

            raw_media = progress.get("photo_file_ids")

            if raw_media:
                media_items = _parse_media_raw(raw_media)
            elif progress.get("photo_file_id"):
                media_items = [
                    {
                        "type": "photo",
                        "file_id": progress.get("photo_file_id"),
                    }
                ]

        item["completed"] = completed
        item["media_items"] = media_items
        item["has_photo"] = bool(media_items)
        item["photo_count"] = len(media_items)

        if media_items:
            item["photo_file_id"] = media_items[0].get("file_id")
        else:
            item["photo_file_id"] = None

        result.append(item)

    logger.info(
        "📋 get_checklist_items: user=%s location=%s date=%s задач=%s",
        user_id,
        location,
        date,
        len(result),
    )

    return result


def get_categories_stats(user_id: int) -> dict[str, dict] | None:
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


def get_items_by_category(user_id: int, category: str) -> list[dict] | None:
    items = get_checklist_items(user_id)

    if items is None:
        return None

    return [item for item in items if item.get("category") == category]


def get_item_by_id(user_id: int, item_id: int) -> dict | None:
    items = get_checklist_items(user_id)

    if items is None:
        return None

    for item in items:
        if item.get("id") == item_id:
            return item

    return None


def toggle_item(user_id: int, item_id: int) -> bool | None:
    shift = get_active_shift(user_id)

    if not shift:
        logger.warning("toggle_item: нет активной смены у пользователя %s", user_id)
        return None

    location = shift.get("location")
    date = today_msk_str()

    shared_progress = get_shared_progress(location, date)
    progress = shared_progress.get(item_id)

    current_completed = progress.get("completed", 0) == 1 if progress else False
    new_completed = not current_completed

    save_shared_progress(location, date, item_id, new_completed, user_id)

    logger.info(
        "🔁 toggle_item: user=%s item=%s новое_состояние=%s",
        user_id,
        item_id,
        "выполнено" if new_completed else "отменено",
    )

    return new_completed


# =========================================================
# MEDIA SAVE
# =========================================================

def attach_media_to_task(
    user_id: int,
    item_id: int,
    media_items: list,
    channel_message_ids: list,
    mark_done: bool = False,
    task_item: dict | None = None,
    replace: bool = False,  # новый параметр
) -> None:
    """
    Сохраняет медиа не просто как file_id, а с мета-данными.
    Если replace=False – добавляет к существующим.
    Если replace=True – заменяет старые новыми.
    """
    logger.info(
        "💾 attach_media_to_task: user=%s item=%s media_count=%s mark_done=%s replace=%s",
        user_id,
        item_id,
        len(media_items or []),
        mark_done,
        replace,
    )

    shift = get_active_shift(user_id)

    if not shift:
        logger.warning("attach_media_to_task: нет активной смены у пользователя %s", user_id)
        return

    location = shift.get("location")
    date = today_msk_str()

    media_items = _normalize_media_items(media_items)

    if not media_items:
        logger.warning("attach_media_to_task: нет корректных медиа для сохранения")
        return

    if isinstance(channel_message_ids, int):
        channel_message_ids = [channel_message_ids]

    channel_message_ids = channel_message_ids or []

    if task_item is None:
        task_item = get_item_by_id(user_id, item_id) or {}

    user_db = get_user(user_id)
    user_name = full_name(user_db)

    # Получаем существующие данные из БД
    with get_connection() as conn:
        existing = conn.execute(
            """
            SELECT photo_file_ids, photo_channel_message_ids, completed
            FROM checklist_shared_progress
            WHERE location = ? AND date = ? AND item_id = ?
            """,
            (location, date, item_id),
        ).fetchone()

        existing_records = []
        existing_channel_ids = []
        if existing:
            try:
                existing_records = json.loads(existing["photo_file_ids"]) if existing["photo_file_ids"] else []
                if not isinstance(existing_records, list):
                    existing_records = []
            except Exception:
                existing_records = []
            try:
                existing_channel_ids = json.loads(existing["photo_channel_message_ids"]) if existing["photo_channel_message_ids"] else []
                if not isinstance(existing_channel_ids, list):
                    existing_channel_ids = []
            except Exception:
                existing_channel_ids = []

        # Формируем новые записи для медиа
        new_records = []
        new_channel_ids = []

        for index, media in enumerate(media_items):
            channel_message_id = None
            if index < len(channel_message_ids):
                channel_message_id = channel_message_ids[index]
            elif channel_message_ids:
                channel_message_id = channel_message_ids[0]

            new_records.append(
                {
                    "type": media.get("type", "photo"),
                    "file_id": media.get("file_id"),
                    "item_id": item_id,
                    "item_text": task_item.get("text"),
                    "category": task_item.get("category"),
                    "location": location,
                    "date": date,
                    "user_id": user_id,
                    "user_name": user_name,
                    "channel_message_id": channel_message_id,
                    "added_at": time_msk_str(),
                }
            )
            if channel_message_id:
                new_channel_ids.append(channel_message_id)

        if not replace:
            # Добавляем к существующим (избегая дублей по file_id)
            existing_file_ids = {r.get("file_id") for r in existing_records if r.get("file_id")}
            for rec in new_records:
                if rec.get("file_id") not in existing_file_ids:
                    existing_records.append(rec)
                    existing_file_ids.add(rec.get("file_id"))
            # Объединяем channel ids
            existing_channel_ids.extend(new_channel_ids)
            final_records = existing_records
            final_channel_ids = existing_channel_ids
        else:
            final_records = new_records
            final_channel_ids = new_channel_ids

        if mark_done:
            save_shared_progress(location, date, item_id, True, user_id)

        payload = json.dumps(final_records, ensure_ascii=False)
        channel_payload = json.dumps(final_channel_ids, ensure_ascii=False)

        first_file_id = final_records[0].get("file_id") if final_records else None
        first_channel_message_id = final_channel_ids[0] if final_channel_ids else None

        if existing:
            conn.execute(
                """
                UPDATE checklist_shared_progress
                SET
                    photo_file_ids = ?,
                    photo_channel_message_ids = ?,
                    photo_file_id = ?,
                    photo_channel_message_id = ?,
                    completed_by = ?,
                    completed = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    payload,
                    channel_payload,
                    first_file_id,
                    first_channel_message_id,
                    user_id,
                    1 if mark_done else 0,
                    time_msk_str() if mark_done else None,
                    existing["id"],
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO checklist_shared_progress (
                    location,
                    date,
                    item_id,
                    completed,
                    completed_at,
                    completed_by,
                    photo_file_id,
                    photo_channel_message_id,
                    photo_file_ids,
                    photo_channel_message_ids
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    location,
                    date,
                    item_id,
                    1 if mark_done else 0,
                    time_msk_str() if mark_done else None,
                    user_id,
                    first_file_id,
                    first_channel_message_id,
                    payload,
                    channel_payload,
                ),
            )

        conn.commit()

    logger.info(
        "✅ attach_media_to_task: медиа сохранены для item=%s location=%s date=%s replace=%s",
        item_id,
        location,
        date,
        replace,
    )


# =========================================================
# PROGRESS
# =========================================================

def get_user_progress_summary(user_id: int):
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


# =========================================================
# TEXT BUILDERS
# =========================================================

def item_detail_text(item: dict) -> str:
    status_text = "✅ Выполнено" if item.get("completed") else "⚪️ Не выполнено"
    category_label = CATEGORY_NAMES.get(item.get("category"), item.get("category"))

    photo_count = item.get("photo_count", 0)

    if photo_count > 0:
        photo_text = f"🖼 Вложений: {photo_count} шт."
    else:
        photo_text = "🖼 Вложений: нет"

    lines = [
        "📌 Задача",
        "",
        item.get("text") or "",
        "",
        f"📂 Категория: {category_label}",
        f"Статус: {status_text}",
        photo_text,
    ]

    if item.get("requires_photo") and not item.get("completed"):
        lines.append("")
        lines.append("⚠️ Для выполнения этой задачи нужно фото.")

    return "\n".join(lines)


def build_photo_caption(user_id: int, item: dict, location: str | None = None) -> str:
    user_db = get_user(user_id)

    user_name = full_name(user_db)

    if not location:
        shift = get_active_shift(user_id)
        location = shift.get("location") if shift else None

    location_label = LOCATIONS.get(location, location or "—")
    category_label = CATEGORY_NAMES.get(item.get("category"), item.get("category") or "")

    today = today_msk_str()
    now_time = time_msk_str()

    caption = (
        "📸 Фотоотчёт по задаче\n\n"
        f"👤 {user_name}\n"
        f"📍 {location_label}\n"
        f"📅 {today}\n"
        f"🕒 {now_time}\n"
    )

    if category_label:
        caption += f"📂 {category_label}\n"

    caption += (
        "\n"
        "📌 Задача:\n"
        f"{item.get('text')}"
    )

    if len(caption) > 1000:
        caption = caption[:1000] + "…"

    return caption