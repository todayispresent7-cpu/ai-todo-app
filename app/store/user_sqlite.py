from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Optional


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class UserRecord:
    id: int
    username: str
    password_hash: str
    created_at: datetime


class SqliteUserStore:
    def __init__(self, db_path: Optional[str] = None) -> None:
        self._path = Path(db_path or "todos.db").resolve()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._path), check_same_thread=False)

    def _init_schema(self) -> None:
        # users 테이블과 todos.user_id 컬럼을 보장
        with self._lock:
            conn = self._conn()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                # todos.user_id 컬럼이 없을 수 있으므로 시도
                try:
                    conn.execute("ALTER TABLE todos ADD COLUMN user_id INTEGER")
                except sqlite3.OperationalError:
                    # 이미 존재하거나 테이블이 없으면 무시
                    pass
                conn.commit()
            finally:
                conn.close()

    def _row_to_user(self, row: tuple) -> UserRecord:
        return UserRecord(
            id=row[0],
            username=row[1],
            password_hash=row[2],
            created_at=datetime.fromisoformat(row[3].replace("Z", "+00:00")),
        )

    def get_by_username(self, username: str) -> Optional[UserRecord]:
        with self._lock:
            conn = self._conn()
            try:
                cur = conn.execute(
                    "SELECT id, username, password_hash, created_at FROM users WHERE username = ?",
                    (username,),
                )
                row = cur.fetchone()
                return self._row_to_user(row) if row else None
            finally:
                conn.close()

    def get(self, user_id: int) -> Optional[UserRecord]:
        with self._lock:
            conn = self._conn()
            try:
                cur = conn.execute(
                    "SELECT id, username, password_hash, created_at FROM users WHERE id = ?",
                    (user_id,),
                )
                row = cur.fetchone()
                return self._row_to_user(row) if row else None
            finally:
                conn.close()

    def list(self) -> list[UserRecord]:
        with self._lock:
            conn = self._conn()
            try:
                cur = conn.execute(
                    "SELECT id, username, password_hash, created_at FROM users ORDER BY id"
                )
                return [self._row_to_user(row) for row in cur.fetchall()]
            finally:
                conn.close()

    def create(self, username: str, password_hash: str) -> UserRecord:
        now = _now()
        with self._lock:
            conn = self._conn()
            try:
                cur = conn.execute(
                    "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                    (username, password_hash, now.isoformat()),
                )
                conn.commit()
                user_id = cur.lastrowid
                return UserRecord(
                    id=user_id,
                    username=username,
                    password_hash=password_hash,
                    created_at=now,
                )
            finally:
                conn.close()

    def delete(self, user_id: int) -> bool:
        with self._lock:
            conn = self._conn()
            try:
                cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
                conn.commit()
                return cur.rowcount > 0
            finally:
                conn.close()


user_store = SqliteUserStore()

