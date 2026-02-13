"""
Database: connection manager, schema initialization, activity logging.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime

from app.config import DB_PATH


@contextmanager
def get_db():
    """Database connection context manager."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize the database."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'Backlog',
                priority TEXT DEFAULT 'Medium',
                agent TEXT DEFAULT 'Unassigned',
                due_date TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                board TEXT DEFAULT 'tasks'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                action TEXT NOT NULL,
                agent TEXT,
                details TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                agent TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS action_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                comment_id INTEGER,
                agent TEXT NOT NULL,
                content TEXT NOT NULL,
                item_type TEXT DEFAULT 'question',
                resolved INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                resolved_at TEXT
            )
        """)
        # Add columns if they don't exist
        for alter in [
            "ALTER TABLE tasks ADD COLUMN working_agent TEXT DEFAULT NULL",
            "ALTER TABLE tasks ADD COLUMN agent_session_key TEXT DEFAULT NULL",
            "ALTER TABLE action_items ADD COLUMN archived INTEGER DEFAULT 0",
            "ALTER TABLE tasks ADD COLUMN source_file TEXT DEFAULT NULL",
            "ALTER TABLE tasks ADD COLUMN source_ref TEXT DEFAULT NULL",
        ]:
            try:
                conn.execute(alter)
            except:
                pass

        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_key TEXT DEFAULT 'main',
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                attachments TEXT,
                created_at TEXT NOT NULL
            )
        """)
        try:
            conn.execute("ALTER TABLE chat_messages ADD COLUMN session_key TEXT DEFAULT 'main'")
        except:
            pass

        conn.execute("""
            CREATE TABLE IF NOT EXISTS deleted_sessions (
                session_key TEXT PRIMARY KEY,
                deleted_at TEXT NOT NULL
            )
        """)
        conn.commit()


def log_activity(task_id: int, action: str, agent: str = None, details: str = None):
    """Log an activity."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO activity_log (task_id, action, agent, details, timestamp) VALUES (?, ?, ?, ?, ?)",
            (task_id, action, agent, details, datetime.now().isoformat())
        )
        conn.commit()
