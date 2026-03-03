"""
database.py — SQLite schema for FocusFlow. Migration-safe.
"""
import sqlite3
import os


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS folders (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            color      TEXT    DEFAULT '#6366F1',
            icon       TEXT    DEFAULT '📁',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS pages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id   INTEGER,
            folder_id   INTEGER,
            title       TEXT    DEFAULT 'Untitled Page',
            content     TEXT    DEFAULT '',
            tags        TEXT    DEFAULT '',
            is_favorite INTEGER DEFAULT 0,
            is_archived INTEGER DEFAULT 0,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES pages(id) ON DELETE CASCADE,
            FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id    INTEGER,
            title      TEXT NOT NULL,
            status     TEXT DEFAULT 'todo',
            due_date   TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS attachments (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id    INTEGER NOT NULL,
            file_name  TEXT,
            file_path  TEXT,
            file_type  TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS pomodoro_history (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id          INTEGER,
            duration_minutes INTEGER DEFAULT 25,
            type             TEXT    DEFAULT 'Focus',
            completed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
    """)

    # Migration: add columns that may not exist in older DBs
    migrations = [
        "ALTER TABLE pages ADD COLUMN folder_id INTEGER",
        "ALTER TABLE pages ADD COLUMN tags TEXT DEFAULT ''",
        "ALTER TABLE pages ADD COLUMN is_favorite INTEGER DEFAULT 0",
        "ALTER TABLE attachments ADD COLUMN file_type TEXT",
    ]
    for sql in migrations:
        try:
            cur.execute(sql)
        except Exception:
            pass   # Column already exists

    conn.commit()
    return conn
