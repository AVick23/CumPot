import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "bot.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _get_columns(conn, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def init_db():
    with get_connection() as conn:
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

        conn.execute("""
            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date TEXT,
                location TEXT,
                start_time TEXT,
                active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(tg_id)
            )
        """)

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

        conn.execute("""
            CREATE TABLE IF NOT EXISTS checklist_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_id INTEGER,
                date TEXT,
                completed BOOLEAN DEFAULT 0,
                completed_at TEXT
            )
        """)

        # Миграция для старой базы
        user_columns = _get_columns(conn, "users")

        if "full_name" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN full_name TEXT")

        if "position" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN position TEXT")

        conn.commit()

    from .checklist import import_checklist_items
    import_checklist_items()


init_db()