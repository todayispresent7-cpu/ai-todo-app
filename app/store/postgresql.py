"""
PostgreSQL 기반 할 일 저장소. SQLAlchemy를 사용합니다.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import Todo
from app.store.memory import TodoRecord


class PostgresTodoStore:
    """
    PostgreSQL 기반 저장소. 동일한 인터페이스(list/get/create/update/delete)를 제공합니다.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _model_to_record(self, todo: Todo) -> TodoRecord:
        return TodoRecord(
            id=todo.id,
            title=todo.title,
            description=todo.description,
            done=todo.done,
            created_at=todo.created_at,
            updated_at=todo.updated_at,
        )

    async def list(self, user_id: int) -> List[TodoRecord]:
        stmt = select(Todo).where(Todo.user_id == user_id).order_by(Todo.id)
        result = await self.session.execute(stmt)
        todos = result.scalars().all()
        return [self._model_to_record(todo) for todo in todos]

    async def get(self, todo_id: int, user_id: int) -> Optional[TodoRecord]:
        stmt = select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
        result = await self.session.execute(stmt)
        todo = result.scalar_one_or_none()
        return self._model_to_record(todo) if todo else None

    async def create(self, title: str, description: Optional[str], user_id: int) -> TodoRecord:
        todo = Todo(
            title=title,
            description=description,
            user_id=user_id,
        )
        self.session.add(todo)
        await self.session.commit()
        await self.session.refresh(todo)
        return self._model_to_record(todo)

    async def update(
        self,
        todo_id: int,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        done: Optional[bool] = None,
        user_id: int,
    ) -> Optional[TodoRecord]:
        # 먼저 기존 레코드를 확인
        stmt = select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
        result = await self.session.execute(stmt)
        todo = result.scalar_one_or_none()
        
        if not todo:
            return None

        # 업데이트할 필드 설정
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if done is not None:
            update_data["done"] = done
        
        if update_data:
            update_data["updated_at"] = func.now()
            stmt = (
                update(Todo)
                .where(Todo.id == todo_id, Todo.user_id == user_id)
                .values(**update_data)
                .returning(Todo)
            )
            result = await self.session.execute(stmt)
            updated_todo = result.scalar_one_or_none()
            await self.session.commit()
            return self._model_to_record(updated_todo) if updated_todo else None
        
        return self._model_to_record(todo)

    async def delete(self, todo_id: int, user_id: int) -> bool:
        stmt = delete(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def delete_by_user(self, user_id: int) -> int:
        stmt = delete(Todo).where(Todo.user_id == user_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def count_all(self) -> int:
        stmt = select(func.count(Todo.id))
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_done(self) -> int:
        stmt = select(func.count(Todo.id)).where(Todo.done == True)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_by_user(self, user_id: int) -> int:
        stmt = select(func.count(Todo.id)).where(Todo.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_done_by_user(self, user_id: int) -> int:
        stmt = select(func.count(Todo.id)).where(Todo.user_id == user_id, Todo.done == True)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
