"""
database/db_manager.py
SQLite persistence layer with security tables.
"""

import sqlite3
import threading
import logging
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from contextlib import contextmanager

import config

logger = logging.getLogger(__name__)
logger.disabled = True

_LOCK = threading.Lock()


class DBManager:
    def __init__(self, db_path: str):
        self._path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _db_conn(self):
        """Custom context manager that commits/rolls back transactions and closes the connection."""
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self):
        with _LOCK, self._db_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS excluded_chats (
                    chat_id      INTEGER PRIMARY KEY,
                    username     TEXT,
                    display_name TEXT,
                    added_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS response_logs (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id       INTEGER NOT NULL,
                    sender        TEXT,
                    user_message  TEXT NOT NULL,
                    ai_response   TEXT NOT NULL,
                    provider      TEXT,
                    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS security_logs (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    username    TEXT,
                    activity_type TEXT NOT NULL,
                    description TEXT,
                    severity    TEXT DEFAULT 'medium',
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS blocked_users (
                    user_id     INTEGER PRIMARY KEY,
                    username    TEXT,
                    reason      TEXT,
                    blocked_until TIMESTAMP,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS appointments (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    username    TEXT,
                    date_time   TEXT,
                    description TEXT,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            default_settings = [
                ("automation_active", "0"),
                ("scope_mode", "exclude"),
                ("ignore_groups", "1"),
                ("AI_PROVIDER", config.AI_PROVIDER),
                ("security_enabled", "1" if config.SECURITY_ENABLED else "0"),
                ("auto_block_threshold", str(config.AUTO_BLOCK_THRESHOLD)),
                ("block_duration_minutes", str(config.BLOCK_DURATION_MINUTES)),
                ("max_messages_per_minute", str(config.MAX_MESSAGES_PER_MINUTE)),
                ("ai_system_prompt", config.AI_SYSTEM_PROMPT),
                ("TELEGRAM_API_ID", str(config.TELEGRAM_API_ID)),
                ("TELEGRAM_API_HASH", config.TELEGRAM_API_HASH),
                ("TELEGRAM_SESSION_NAME", config.TELEGRAM_SESSION_NAME),
                ("OWNER_USERNAME", config.OWNER_USERNAME),
                ("DEEPSEEK_API_KEY", config.DEEPSEEK_API_KEY),
                ("DEEPSEEK_MODEL", config.DEEPSEEK_MODEL),
                ("DEEPSEEK_BASE_URL", config.DEEPSEEK_BASE_URL),
                ("GEMINI_API_KEY", config.GEMINI_API_KEY),
                ("GEMINI_MODEL", config.GEMINI_MODEL),
                ("GEMINI_BASE_URL", config.GEMINI_BASE_URL),
            ]
            for key, value in default_settings:
                conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with _LOCK, self._db_conn() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        with _LOCK, self._db_conn() as conn:
            conn.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))

    def add_excluded_chat(self, chat_id: int, username: str = "", display_name: str = ""):
        with _LOCK, self._db_conn() as conn:
            conn.execute("INSERT OR REPLACE INTO excluded_chats (chat_id, username, display_name) VALUES (?, ?, ?)", (chat_id, username, display_name))

    def remove_excluded_chat(self, chat_id: int):
        with _LOCK, self._db_conn() as conn:
            conn.execute("DELETE FROM excluded_chats WHERE chat_id = ?", (chat_id,))

    def get_excluded_chats(self) -> List[Dict]:
        with _LOCK, self._db_conn() as conn:
            rows = conn.execute("SELECT chat_id, username, display_name FROM excluded_chats ORDER BY added_at DESC").fetchall()
            return [dict(row) for row in rows]

    def is_excluded(self, chat_id: int) -> bool:
        with _LOCK, self._db_conn() as conn:
            row = conn.execute("SELECT 1 FROM excluded_chats WHERE chat_id = ?", (chat_id,)).fetchone()
            return row is not None

    def log_response(self, chat_id: int, sender: str, user_message: str, ai_response: str, provider: str):
        with _LOCK, self._db_conn() as conn:
            conn.execute("INSERT INTO response_logs (chat_id, sender, user_message, ai_response, provider) VALUES (?, ?, ?, ?, ?)", (chat_id, sender, user_message, ai_response, provider))

    def get_recent_logs(self, limit: int = 100) -> List[Dict]:
        with _LOCK, self._db_conn() as conn:
            rows = conn.execute("SELECT * FROM response_logs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(row) for row in rows]

    def log_security_event(self, user_id: int, username: str, activity_type: str, description: str, severity: str = "medium"):
        with _LOCK, self._db_conn() as conn:
            conn.execute("INSERT INTO security_logs (user_id, username, activity_type, description, severity) VALUES (?, ?, ?, ?, ?)", (user_id, username, activity_type, description, severity))

    def get_security_logs(self, limit: int = 100) -> List[Dict]:
        with _LOCK, self._db_conn() as conn:
            rows = conn.execute("SELECT * FROM security_logs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(row) for row in rows]

    def is_user_blocked(self, user_id: int) -> tuple[bool, Optional[str]]:
        with _LOCK, self._db_conn() as conn:
            row = conn.execute("SELECT reason, blocked_until FROM blocked_users WHERE user_id = ?", (user_id,)).fetchone()
            if row:
                blocked_until = row["blocked_until"]
                if blocked_until:
                    blocked_until_dt = datetime.fromisoformat(blocked_until)
                    if blocked_until_dt > datetime.now():
                        return True, row["reason"]
                    else:
                        conn.execute("DELETE FROM blocked_users WHERE user_id = ?", (user_id,))
                        return False, None
                return True, row["reason"]
            return False, None

    def block_user(self, user_id: int, username: str, reason: str, duration_minutes: int = 60):
        blocked_until = (datetime.now() + timedelta(minutes=duration_minutes)).isoformat()
        with _LOCK, self._db_conn() as conn:
            conn.execute("INSERT OR REPLACE INTO blocked_users (user_id, username, reason, blocked_until) VALUES (?, ?, ?, ?)", (user_id, username, reason, blocked_until))

    def unblock_user(self, user_id: int):
        with _LOCK, self._db_conn() as conn:
            conn.execute("DELETE FROM blocked_users WHERE user_id = ?", (user_id,))

    def get_all_blocked_users(self) -> List[Dict]:
        with _LOCK, self._db_conn() as conn:
            rows = conn.execute("SELECT user_id, username, reason, blocked_until FROM blocked_users WHERE blocked_until > datetime('now')").fetchall()
            return [dict(row) for row in rows]

    def get_violation_count(self, user_id: int, severity: Optional[str] = None, hours: int = 24) -> int:
        with _LOCK, self._db_conn() as conn:
            if severity:
                row = conn.execute(
                    f"SELECT COUNT(*) FROM security_logs WHERE user_id = ? AND severity = ? AND created_at > datetime('now', '-{hours} hours')",
                    (user_id, severity)
                ).fetchone()
            else:
                row = conn.execute(
                    f"SELECT COUNT(*) FROM security_logs WHERE user_id = ? AND severity IN ('high', 'medium') AND created_at > datetime('now', '-{hours} hours')",
                    (user_id,)
                ).fetchone()
            return row[0] if row else 0

    def add_appointment(self, user_id: int, username: str, date_time: str, description: str):
        with _LOCK, self._db_conn() as conn:
            conn.execute("INSERT INTO appointments (user_id, username, date_time, description) VALUES (?, ?, ?, ?)", 
                         (user_id, username, date_time, description))

    def get_appointments(self, limit: int = 100) -> List[Dict]:
        with _LOCK, self._db_conn() as conn:
            rows = conn.execute("SELECT * FROM appointments ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(row) for row in rows]

    def delete_appointment(self, appointment_id: int):
        with _LOCK, self._db_conn() as conn:
            conn.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))