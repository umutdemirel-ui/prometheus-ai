"""SQLite persistent memory for Prometheus (notes, reminders, timers, history)."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from prometheus.config import DATA_DIR


class PrometheusMemory:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or (DATA_DIR / "prometheus.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS command_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    response TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS timers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label TEXT NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    fire_at REAL NOT NULL,
                    fired INTEGER NOT NULL DEFAULT 0
                );
                """
            )

    def add_note(self, content: str) -> Dict[str, Any]:
        now = time.time()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO notes (content, created_at) VALUES (?, ?)",
                (content.strip(), now),
            )
            return {"id": cur.lastrowid, "content": content.strip(), "created_at": now}

    def list_notes(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, content, created_at FROM notes ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_note(self, note_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            return cur.rowcount > 0

    def clear_notes(self) -> int:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM notes")
            return cur.rowcount

    def log_command(
        self, command: str, intent: str, response: str, success: bool = True
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO command_history (command, intent, response, success, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (command, intent, response, 1 if success else 0, time.time()),
            )

    def get_history(self, limit: int = 30) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, command, intent, response, success, created_at
                FROM command_history ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def add_timer(self, label: str, duration_seconds: int) -> Dict[str, Any]:
        fire_at = time.time() + duration_seconds
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO timers (label, duration_seconds, fire_at, fired) VALUES (?, ?, ?, 0)",
                (label, duration_seconds, fire_at),
            )
            return {
                "id": cur.lastrowid,
                "label": label,
                "duration_seconds": duration_seconds,
                "fire_at": fire_at,
            }

    def poll_due_timers(self) -> List[Dict[str, Any]]:
        now = time.time()
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, label, duration_seconds, fire_at FROM timers WHERE fired = 0 AND fire_at <= ?",
                (now,),
            ).fetchall()
            due = [dict(r) for r in rows]
            if due:
                ids = [(r["id"],) for r in due]
                conn.executemany("UPDATE timers SET fired = 1 WHERE id = ?", ids)
            return due

    def list_active_timers(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, label, duration_seconds, fire_at FROM timers WHERE fired = 0 ORDER BY fire_at ASC"
            ).fetchall()
            return [dict(r) for r in rows]
