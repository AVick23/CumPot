import os
import sqlite3
import json

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

        # Таблица общего прогресса – добавляем поля для списка файлов
        conn.execute("""
            CREATE TABLE IF NOT EXISTS checklist_shared_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location TEXT NOT NULL,
                date TEXT NOT NULL,
                item_id INTEGER NOT NULL,
                completed BOOLEAN DEFAULT 0,
                completed_at TEXT,
                completed_by INTEGER,
                photo_file_id TEXT,                 -- оставлено для обратной совместимости
                photo_channel_message_id INTEGER,   -- оставлено для обратной совместимости
                photo_file_ids TEXT,                -- JSON-массив file_id
                photo_channel_message_ids TEXT,     -- JSON-массив message_id канала
                FOREIGN KEY (item_id) REFERENCES checklist_items(id)
            )
        """)
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_shared_progress
            ON checklist_shared_progress(location, date, item_id)
        """)

        # Таблица для отслеживания отправленных уведомлений
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

        # Миграции для checklist_items
        item_columns = _get_columns(conn, "checklist_items")
        if "requires_photo" not in item_columns:
            conn.execute("ALTER TABLE checklist_items ADD COLUMN requires_photo BOOLEAN DEFAULT 0")
        if "requires_notification" not in item_columns:
            conn.execute("ALTER TABLE checklist_items ADD COLUMN requires_notification BOOLEAN DEFAULT 0")
        if "notification_time" not in item_columns:
            conn.execute("ALTER TABLE checklist_items ADD COLUMN notification_time TEXT")
        if "due_date" not in item_columns:
            conn.execute("ALTER TABLE checklist_items ADD COLUMN due_date TEXT")
        if "is_recurring" not in item_columns:
            conn.execute("ALTER TABLE checklist_items ADD COLUMN is_recurring BOOLEAN DEFAULT 1")
        if "days_of_week" not in item_columns:
            conn.execute("ALTER TABLE checklist_items ADD COLUMN days_of_week TEXT")
            conn.execute("UPDATE checklist_items SET days_of_week = CAST(day_of_week AS TEXT) WHERE day_of_week IS NOT NULL")

        # Миграции для checklist_shared_progress – добавляем новые поля
        progress_columns = _get_columns(conn, "checklist_shared_progress")
        if "photo_file_ids" not in progress_columns:
            conn.execute("ALTER TABLE checklist_shared_progress ADD COLUMN photo_file_ids TEXT")
        if "photo_channel_message_ids" not in progress_columns:
            conn.execute("ALTER TABLE checklist_shared_progress ADD COLUMN photo_channel_message_ids TEXT")

        conn.commit()

    # Импорт стартовых чек-листов и типов смен
    from .checklist import import_checklist_items
    import_checklist_items()

    from .shifts import import_shift_types
    import_shift_types()


init_db()