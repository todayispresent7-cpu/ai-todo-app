from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List, Optional


def _now() -> datetime:
    # 시간은 UTC로 저장(일관성)하고, 클라이언트가 필요하면 변환하도록 합니다.
    return datetime.now(timezone.utc)


@dataclass
class TodoRecord:
    # 내부 저장용 레코드(응답 스키마와 분리)
    id: int
    title: str
    description: Optional[str]
    done: bool
    created_at: datetime
    updated_at: datetime


class InMemoryTodoStore:
    """
    아주 단순한 메모리 기반 저장소입니다.
    - 서버 재시작 시 데이터가 초기화됩니다.
    - 동시 요청에서 ID/데이터가 꼬이지 않도록 Lock을 사용합니다.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._next_id = 1
        self._todos: Dict[int, TodoRecord] = {}

    def list(self) -> List[TodoRecord]:
        with self._lock:
            # id 오름차순으로 반환
            return [self._todos[k] for k in sorted(self._todos.keys())]

    def get(self, todo_id: int) -> Optional[TodoRecord]:
        with self._lock:
            return self._todos.get(todo_id)

    def create(self, title: str, description: Optional[str]) -> TodoRecord:
        with self._lock:
            todo_id = self._next_id
            self._next_id += 1
            now = _now()
            rec = TodoRecord(
                id=todo_id,
                title=title,
                description=description,
                done=False,
                created_at=now,
                updated_at=now,
            )
            self._todos[todo_id] = rec
            return rec

    def update(
        self,
        todo_id: int,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        done: Optional[bool] = None,
    ) -> Optional[TodoRecord]:
        with self._lock:
            rec = self._todos.get(todo_id)
            if rec is None:
                return None

            changed = False
            if title is not None and title != rec.title:
                rec.title = title
                changed = True
            if description is not None and description != rec.description:
                rec.description = description
                changed = True
            if done is not None and done != rec.done:
                rec.done = done
                changed = True

            if changed:
                rec.updated_at = _now()
            return rec

    def delete(self, todo_id: int) -> bool:
        with self._lock:
            return self._todos.pop(todo_id, None) is not None


# 앱 전역에서 공유하는 단일 스토어 인스턴스
todo_store = InMemoryTodoStore()

