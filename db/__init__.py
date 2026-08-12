import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "bot.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


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
                days TEXT NOT NULL,  -- 'all' или 'mon,tue,wed,...' или 'sat,sun'
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
                sort_order INTEGER,
                text TEXT
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
                FOREIGN KEY (item_id) REFERENCES checklist_items(id)
            )
        """)
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_shared_progress
            ON checklist_shared_progress(location, date, item_id)
        """)

        conn.commit()

    # Импорт стартовых чек-листов
    from .checklist import import_checklist_items
    import_checklist_items()

    # Импорт типов смен
    from .shifts import import_shift_types
    import_shift_types()


init_db()