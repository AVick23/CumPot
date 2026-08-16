import logging
from datetime import datetime, time
from db.checklist import get_items_for_location_and_day, is_notification_sent, mark_notification_sent
from db.shifts import get_shifts_for_date
from db.users import get_active_users  # предположим, есть функция получения активных пользователей
from utils.time_utils import now_msk, today_msk_str, yesterday_msk_str
from utils.reminder_builder import get_last_closing_report, build_opening_reminder

logger = logging.getLogger(__name__)

# Хранилище для запланированных задач (чтобы не дублировать)
_scheduled_jobs = set()


def setup_jobs(app):
    """Настраивает периодические задачи через JobQueue."""
    job_queue = app.job_queue
    if job_queue is None:
        logger.error("JobQueue не доступен. Убедитесь, что установлен python-telegram-bot[job-queue]")
        return

    # Запускаем проверку уведомлений каждую минуту
    job_queue.run_repeating(
        check_notifications,
        interval=60,  # секунды
        first=10,     # первый запуск через 10 секунд после старта
    )
    logger.info("🕒 JobQueue: проверка уведомлений запущена (каждую минуту)")

    # Запускаем отправку утреннего напоминания каждый день в 7:00
    job_queue.run_daily(
        send_morning_reminder,
        time=time(hour=7, minute=0),
        days=tuple(range(7)),  # каждый день недели
    )
    logger.info("🌅 JobQueue: утреннее напоминание запланировано на 7:00")


async def check_notifications(context):
    """Проверяет задачи, требующие уведомления, и отправляет их сотрудникам на смене."""
    try:
        now = now_msk()
        today = today_msk_str()
        current_minutes = now.hour * 60 + now.minute

        for location in ("bar", "kitchen"):
            items = get_items_for_location_and_day(location, today)
            if not items:
                continue

            for item in items:
                if not item.get("requires_notification"):
                    continue
                notification_time = item.get("notification_time")
                if not notification_time:
                    continue
                if is_notification_sent(item["id"], today):
                    continue

                try:
                    item_hour, item_minute = map(int, notification_time.split(":"))
                    item_minutes = item_hour * 60 + item_minute
                    if abs(current_minutes - item_minutes) > 2:
                        continue
                except Exception as e:
                    logger.warning(f"Неверный формат времени для задачи {item['id']}: {notification_time} - {e}")
                    continue

                shifts = get_shifts_for_date(today)
                location_shifts = [s for s in shifts if s.get("location") == location]
                if not location_shifts:
                    continue

                for shift in location_shifts:
                    user_id = shift["user_id"]
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=(
                                f"🔔 Напоминание!\n\n"
                                f"Не забудьте выполнить задачу:\n"
                                f"«{item['text']}»\n\n"
                                f"📅 Сегодня, {today}\n"
                                f"📍 {location.capitalize()}"
                            )
                        )
                        logger.info(f"✅ Уведомление отправлено пользователю {user_id} по задаче {item['id']}")
                    except Exception as e:
                        logger.error(f"❌ Не удалось отправить уведомление пользователю {user_id}: {e}")

                mark_notification_sent(item["id"], today)
                logger.info(f"📌 Уведомление по задаче {item['id']} за {today} помечено как отправленное")

    except Exception as e:
        logger.error(f"❌ Ошибка в задаче отправки уведомлений: {e}", exc_info=True)


async def send_morning_reminder(context):
    """
    Отправляет утреннее напоминание на основе последнего отчёта закрытия.
    Отправляется всем активным сотрудникам (или только тем, у кого есть смена сегодня).
    """
    try:
        logger.info("🌅 Запуск утреннего напоминания")

        # Получаем текст последнего отчёта закрытия
        report_text = get_last_closing_report()
        if not report_text:
            logger.info("ℹ️ Нет отчёта закрытия для утреннего напоминания")
            return

        # Строим текст напоминания
        reminder_text = build_opening_reminder(report_text)
        if not reminder_text:
            logger.info("ℹ️ Напоминание пустое, пропускаем")
            return

        # Получаем список активных пользователей
        users = get_active_users()
        if not users:
            logger.info("ℹ️ Нет активных пользователей для отправки напоминания")
            return

        today = today_msk_str()
        # Фильтруем пользователей, у которых есть смена сегодня (или отправляем всем)
        # В зависимости от задачи: можно отправлять всем активным, либо только тем, кто сегодня на смене.
        # Для примера отправляем всем активным.
        recipients = [user["tg_id"] for user in users]

        if not recipients:
            logger.info("ℹ️ Нет получателей для утреннего напоминания")
            return

        # Отправляем каждому
        for user_id in recipients:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=reminder_text,
                    parse_mode="Markdown"
                )
                logger.info(f"✅ Утреннее напоминание отправлено пользователю {user_id}")
            except Exception as e:
                logger.error(f"❌ Не удалось отправить утреннее напоминание пользователю {user_id}: {e}")

        logger.info("🌅 Утреннее напоминание завершено")

    except Exception as e:
        logger.error(f"❌ Ошибка в задаче утреннего напоминания: {e}", exc_info=True)