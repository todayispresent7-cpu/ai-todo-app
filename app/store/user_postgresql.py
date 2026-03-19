from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import User


@dataclass
class UserRecord:
    id: int
    username: str
    password_hash: str
    created_at: datetime


class PostgresUserStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _model_to_user(self, user: User) -> UserRecord:
        return UserRecord(
            id=user.id,
            username=user.username,
            password_hash=user.password_hash,
            created_at=user.created_at,
        )

    async def get_by_username(self, username: str) -> Optional[UserRecord]:
        stmt = select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        return self._model_to_user(user) if user else None

    async def get(self, user_id: int) -> Optional[UserRecord]:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        return self._model_to_user(user) if user else None

    async def list(self) -> list[UserRecord]:
        stmt = select(User).order_by(User.id)
        result = await self.session.execute(stmt)
        users = result.scalars().all()
        return [self._model_to_user(user) for user in users]

    async def create(self, username: str, password_hash: str) -> UserRecord:
        user = User(
            username=username,
            password_hash=password_hash,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return self._model_to_user(user)

    async def delete(self, user_id: int) -> bool:
        stmt = delete(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
