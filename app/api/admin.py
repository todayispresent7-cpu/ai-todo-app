from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import case, delete, func, select

from app.api.auth import get_current_user
from app.db import get_db
from app.db_models import Todo, User
from app.models.todo import TodoOut
from app.models.user import UserOut
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(current_user=Depends(get_current_user)) -> User:
    if current_user.username != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자만 접근할 수 있습니다.",
        )
    return current_user


def _todo_to_out(rec) -> TodoOut:
    return TodoOut(
        id=rec.id,
        title=rec.title,
        description=rec.description,
        done=rec.done,
        created_at=rec.created_at,
        updated_at=rec.updated_at,
    )


class AdminUserRow(BaseModel):
    id: int
    username: str
    created_at: datetime
    todo_total: int
    todo_done: int
    todo_done_rate: float


class AdminUserTodosOut(BaseModel):
    user: UserOut
    summary: AdminUserRow
    todos: list[TodoOut]


class AdminStatsOut(BaseModel):
    total_users: int
    total_todos: int
    done_todos: int
    done_rate: float


@router.get("/users", response_model=list[AdminUserRow])
async def admin_list_users(
    _: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    todo_total = func.count(Todo.id)
    todo_done = func.coalesce(func.sum(case((Todo.done.is_(True), 1), else_=0)), 0)
    stmt = (
        select(User.id, User.username, User.created_at, todo_total, todo_done)
        .select_from(User)
        .outerjoin(Todo, Todo.user_id == User.id)
        .group_by(User.id)
        .order_by(User.id)
    )
    rows = (await db.execute(stmt)).all()
    out: list[AdminUserRow] = []
    for (uid, username, created_at, total, done) in rows:
        total_i = int(total or 0)
        done_i = int(done or 0)
        rate = (done_i / total_i) if total_i else 0.0
        out.append(
            AdminUserRow(
                id=int(uid),
                username=str(username),
                created_at=created_at,
                todo_total=total_i,
                todo_done=done_i,
                todo_done_rate=rate,
            )
        )
    return out


@router.get("/users/{user_id}/todos", response_model=AdminUserTodosOut)
async def admin_get_user_todos(
    user_id: int,
    _: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    u = await db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")

    todo_rows = await db.scalars(select(Todo).where(Todo.user_id == user_id).order_by(Todo.id))
    todos = [_todo_to_out(r) for r in list(todo_rows)]
    total = len(todos)
    done = len([t for t in todos if t.done])
    rate = (done / total) if total else 0.0

    user_out = UserOut(id=u.id, username=u.username, created_at=u.created_at)
    summary = AdminUserRow(
        id=u.id,
        username=u.username,
        created_at=u.created_at,
        todo_total=total,
        todo_done=done,
        todo_done_rate=rate,
    )
    return AdminUserTodosOut(user=user_out, summary=summary, todos=todos)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_user(
    user_id: int,
    _: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    u = await db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    if u.username == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="admin 계정은 삭제할 수 없습니다.",
        )

    await db.delete(u)
    await db.commit()
    return None


@router.get("/stats", response_model=AdminStatsOut)
async def admin_stats(
    _: User = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    total_users = int((await db.scalar(select(func.count()).select_from(User))) or 0)
    total_todos = int((await db.scalar(select(func.count()).select_from(Todo))) or 0)
    done_todos = int(
        (await db.scalar(select(func.count()).select_from(Todo).where(Todo.done.is_(True)))) or 0
    )
    done_rate = (done_todos / total_todos) if total_todos else 0.0
    return AdminStatsOut(
        total_users=total_users,
        total_todos=total_todos,
        done_todos=done_todos,
        done_rate=done_rate,
    )

