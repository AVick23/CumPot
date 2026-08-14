import os
import sqlite3
import json
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "bot.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _get_columns(conn, table_name):
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def init_db():
    logger.info("Инициализация базы данных...")
    with get_connection() as conn:
        # Таблица пользователей
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                full_name TEXT,
                position TEXT,
                is_admin BOOLEAN DEFAULT 0
            )
        """)

        # Таблица типов смен
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shift_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location TEXT NOT NULL,
                name TEXT NOT NULL,
                start_time TEXT NOT NULL,
                duration INTEGER NOT NULL,
                days TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0
            )
        """)

        # Таблица смен
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                shift_type_id INTEGER,
                date TEXT,
                start_time TEXT,
                active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(tg_id),
                FOREIGN KEY (shift_type_id) REFERENCES shift_types(id)
            )
        """)

        # Таблица пунктов чек-листов
        conn.execute("""
            CREATE TABLE IF NOT EXISTS checklist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                location TEXT,
                category TEXT,
                day_of_week INTEGER,
                days_of_week TEXT,
                sort_order INTEGER,
                text TEXT,
                requires_photo BOOLEAN DEFAULT 0,
                requires_notification BOOLEAN DEFAULT 0,
                notification_time TEXT,
                due_date TEXT,
                is_recurring BOOLEAN DEFAULT 1
            )
        """)

        # Таблица общего прогресса
        conn.execute("""
            CREATE TABLE IF NOT EXISTS checklist_shared_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location TEXT NOT NULL,
                date TEXT NOT NULL,
                item_id INTEGER NOT NULL,
                completed BOOLEAN DEFAULT 0,
                completed_at TEXT,
                completed_by INTEGER,
                photo_file_id TEXT,
                photo_channel_message_id INTEGER,
                photo_file_ids TEXT,
                photo_channel_message_ids TEXT,
                FOREIGN KEY (item_id) REFERENCES checklist_items(id)
            )
        """)
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_shared_progress
            ON checklist_shared_progress(location, date, item_id)
        """)

        # Таблица уведомлений
        conn.execute("""
            CREATE TABLE IF NOT EXISTS checklist_notifications_sent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                sent_at TEXT,
                FOREIGN KEY (item_id) REFERENCES checklist_items(id),
                UNIQUE(item_id, date)
            )
        """)
        
        # Таблица отчётов по сменам
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shift_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                report_type TEXT NOT NULL,
                author_id INTEGER,
                full_text TEXT NOT NULL,
                parsed_data TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (author_id) REFERENCES users(tg_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_reports_date_type
            ON shift_reports (date, report_type)
        """)

        # ------------------------------------------------------------
        # НОВЫЕ ТАБЛИЦЫ (личные данные, ставки, такси)
        # ------------------------------------------------------------

        # Таблица ставок
        conn.execute("""
            CREATE TABLE IF NOT EXISTS salary_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                rate REAL NOT NULL,
                date_from TEXT NOT NULL,
                date_to TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(tg_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_salary_rates_user_date
            ON salary_rates (user_id, date_from)
        """)

        # Таблица расходов на такси
        conn.execute("""
            CREATE TABLE IF NOT EXISTS taxi_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                photo_file_ids TEXT,
                photo_channel_message_ids TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(tg_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_taxi_user_date
            ON taxi_expenses (user_id, date)
        """)

        # ------------------------------------------------------------
        # МИГРАЦИИ ДЛЯ СУЩЕСТВУЮЩИХ ТАБЛИЦ
        # ------------------------------------------------------------

        # Добавляем поля в users
        user_columns = _get_columns(conn, "users")
        new_user_fields = {
            "phone": "TEXT",
            "birthday": "TEXT",
            "address": "TEXT",
            "responsibilities": "TEXT",
            "status": "TEXT DEFAULT 'Сотрудник'",      # НОВОЕ
            "admin_comment": "TEXT",                  # НОВОЕ
        }
        for field, col_type in new_user_fields.items():
            if field not in user_columns:
                logger.info(f"Добавляем колонку {field} в users")
                conn.execute(f"ALTER TABLE users ADD COLUMN {field} {col_type}")

        # Миграции для checklist_items
        item_columns = _get_columns(conn, "checklist_items")
        if "requires_photo" not in item_columns:
            logger.info("Добавляем колонку requires_photo в checklist_items")
            conn.execute("ALTER TABLE checklist_items ADD COLUMN requires_photo BOOLEAN DEFAULT 0")
        if "requires_notification" not in item_columns:
            logger.info("Добавляем колонку requires_notification в checklist_items")
            conn.execute("ALTER TABLE checklist_items ADD COLUMN requires_notification BOOLEAN DEFAULT 0")
        if "notification_time" not in item_columns:
            logger.info("Добавляем колонку notification_time в checklist_items")
            conn.execute("ALTER TABLE checklist_items ADD COLUMN notification_time TEXT")
        if "due_date" not in item_columns:
            logger.info("Добавляем колонку due_date в checklist_items")
            conn.execute("ALTER TABLE checklist_items ADD COLUMN due_date TEXT")
        if "is_recurring" not in item_columns:
            logger.info("Добавляем колонку is_recurring в checklist_items")
            conn.execute("ALTER TABLE checklist_items ADD COLUMN is_recurring BOOLEAN DEFAULT 1")
        if "days_of_week" not in item_columns:
            logger.info("Добавляем колонку days_of_week в checklist_items")
            conn.execute("ALTER TABLE checklist_items ADD COLUMN days_of_week TEXT")
            conn.execute("UPDATE checklist_items SET days_of_week = CAST(day_of_week AS TEXT) WHERE day_of_week IS NOT NULL")

        # Миграции для checklist_shared_progress
        progress_columns = _get_columns(conn, "checklist_shared_progress")
        if "photo_file_ids" not in progress_columns:
            logger.info("Добавляем колонку photo_file_ids в checklist_shared_progress")
            conn.execute("ALTER TABLE checklist_shared_progress ADD COLUMN photo_file_ids TEXT")
        if "photo_channel_message_ids" not in progress_columns:
            logger.info("Добавляем колонку photo_channel_message_ids в checklist_shared_progress")
            conn.execute("ALTER TABLE checklist_shared_progress ADD COLUMN photo_channel_message_ids TEXT")

        conn.commit()

    # Импорт стартовых чек-листов и типов смен
    from .checklist import import_checklist_items
    import_checklist_items()

    from .shifts import import_shift_types
    import_shift_types()
    logger.info("Инициализация базы данных завершена.")


# Инициализация при первом импорте (по-прежнему вызывается)
init_db()