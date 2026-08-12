import os
import sqlite3

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

        # Таблица пунктов чек-листов (обновлена)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS checklist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,                   -- 'daily', 'weekly', 'once'
                location TEXT,               -- 'bar' или 'kitchen'
                category TEXT,               -- 'opening', 'daytime', 'closing', 'weekly'
                day_of_week INTEGER,         -- 0-6 для weekly, NULL для других
                sort_order INTEGER,
                text TEXT,
                requires_photo BOOLEAN DEFAULT 0,
                requires_notification BOOLEAN DEFAULT 0,
                due_date TEXT,               -- YYYY-MM-DD для type='once', NULL для остальных
                is_recurring BOOLEAN DEFAULT 1  -- 1 — постоянная, 0 — одноразовая
            )
        """)

        # Таблица общего прогресса (без изменений)
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

        # Безопасная миграция для старых баз
        item_columns = _get_columns(conn, "checklist_items")
        if "requires_photo" not in item_columns:
            conn.execute("ALTER TABLE checklist_items ADD COLUMN requires_photo BOOLEAN DEFAULT 0")
        if "requires_notification" not in item_columns:
            conn.execute("ALTER TABLE checklist_items ADD COLUMN requires_notification BOOLEAN DEFAULT 0")
        if "due_date" not in item_columns:
            conn.execute("ALTER TABLE checklist_items ADD COLUMN due_date TEXT")
        if "is_recurring" not in item_columns:
            conn.execute("ALTER TABLE checklist_items ADD COLUMN is_recurring BOOLEAN DEFAULT 1")
        # Если есть записи с type='daily' или 'weekly', установим is_recurring=1 (уже по умолчанию)

        conn.commit()

    # Импорт стартовых чек-листов
    from .checklist import import_checklist_items
    import_checklist_items()

    # Импорт типов смен
    from .shifts import import_shift_types
    import_shift_types()


init_db()