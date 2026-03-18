"""
SQLite 기반 할 일 저장소. 서버 재시작 후에도 데이터가 유지됩니다.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import List, Optional

from app.store.memory import TodoRecord


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


class SqliteTodoStore:
    """
    SQLite 기반 저장소. 동일한 인터페이스(list/get/create/update/delete)를 제공합니다.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._path = Path(db_path or "todos.db").resolve()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._path), check_same_thread=False)

    def _init_schema(self) -> None:
        with self._lock:
            conn = self._conn()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS todos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT,
                        done INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        user_id INTEGER
                    )
                    """
                )
                # 기존 DB에 user_id 컬럼이 없을 수 있으므로 보강
                try:
                    conn.execute("ALTER TABLE todos ADD COLUMN user_id INTEGER")
                except sqlite3.OperationalError:
                    # 이미 존재하거나 테이블이 없으면 무시
                    pass
                conn.commit()
            finally:
                conn.close()

    def _row_to_record(self, row: tuple) -> TodoRecord:
        return TodoRecord(
            id=row[0],
            title=row[1],
            description=row[2],
            done=bool(row[3]),
            created_at=_parse_iso(row[4]),
            updated_at=_parse_iso(row[5]),
        )

    def list(self, user_id: int) -> List[TodoRecord]:
        with self._lock:
            conn = self._conn()
            try:
                cur = conn.execute(
                    "SELECT id, title, description, done, created_at, updated_at FROM todos WHERE user_id = ? ORDER BY id",
                    (user_id,),
                )
                return [self._row_to_record(row) for row in cur.fetchall()]
            finally:
                conn.close()

    def get(self, todo_id: int, user_id: int) -> Optional[TodoRecord]:
        with self._lock:
            conn = self._conn()
            try:
                cur = conn.execute(
                    "SELECT id, title, description, done, created_at, updated_at FROM todos WHERE id = ? AND user_id = ?",
                    (todo_id, user_id),
                )
                row = cur.fetchone()
                return self._row_to_record(row) if row else None
            finally:
                conn.close()

    def create(self, title: str, description: Optional[str], user_id: int) -> TodoRecord:
        now = _now()
        now_str = _iso(now)
        with self._lock:
            conn = self._conn()
            try:
                cur = conn.execute(
                    "INSERT INTO todos (title, description, done, created_at, updated_at, user_id) VALUES (?, ?, 0, ?, ?, ?)",
                    (title, description or "", now_str, now_str, user_id),
                )
                conn.commit()
                todo_id = cur.lastrowid
                return TodoRecord(
                    id=todo_id,
                    title=title,
                    description=description,
                    done=False,
                    created_at=now,
                    updated_at=now,
                )
            finally:
                conn.close()

    def update(
        self,
        todo_id: int,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        done: Optional[bool] = None,
        user_id: int,
    ) -> Optional[TodoRecord]:
        with self._lock:
            conn = self._conn()
            try:
                cur = conn.execute(
                    "SELECT id, title, description, done, created_at, updated_at FROM todos WHERE id = ? AND user_id = ?",
                    (todo_id, user_id),
                )
                row = cur.fetchone()
                if not row:
                    return None
                rec = self._row_to_record(row)

                new_title = title if title is not None else rec.title
                new_desc = description if description is not None else rec.description
                new_done = done if done is not None else rec.done
                new_updated = _now()

                conn.execute(
                    "UPDATE todos SET title = ?, description = ?, done = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                    (new_title, new_desc or "", 1 if new_done else 0, _iso(new_updated), todo_id, user_id),
                )
                conn.commit()
                return TodoRecord(
                    id=todo_id,
                    title=new_title,
                    description=new_desc,
                    done=new_done,
                    created_at=rec.created_at,
                    updated_at=new_updated,
                )
            finally:
                conn.close()

    def delete(self, todo_id: int, user_id: int) -> bool:
        with self._lock:
            conn = self._conn()
            try:
                cur = conn.execute("DELETE FROM todos WHERE id = ? AND user_id = ?", (todo_id, user_id))
                conn.commit()
                return cur.rowcount > 0
            finally:
                conn.close()


# 앱 전역에서 사용하는 SQLite 스토어 (서버 재시작 후에도 유지)
todo_store = SqliteTodoStore()
