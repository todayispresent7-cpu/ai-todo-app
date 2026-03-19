from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.models.todo import TodoOut
from app.models.user import UserOut
from app.store.sqlite import todo_store
from app.store.user_sqlite import UserRecord, user_store


router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(current_user: UserRecord = Depends(get_current_user)) -> UserRecord:
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
def admin_list_users(_: UserRecord = Depends(_require_admin)):
    users = user_store.list()
    out: list[AdminUserRow] = []
    for u in users:
        total = todo_store.count_by_user(u.id)
        done = todo_store.count_done_by_user(u.id)
        rate = (done / total) if total else 0.0
        out.append(
            AdminUserRow(
                id=u.id,
                username=u.username,
                created_at=u.created_at,
                todo_total=total,
                todo_done=done,
                todo_done_rate=rate,
            )
        )
    return out


@router.get("/users/{user_id}/todos", response_model=AdminUserTodosOut)
def admin_get_user_todos(user_id: int, _: UserRecord = Depends(_require_admin)):
    u = user_store.get(user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")

    todos = [_todo_to_out(r) for r in todo_store.list(user_id=user_id)]
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
def admin_delete_user(user_id: int, _: UserRecord = Depends(_require_admin)):
    u = user_store.get(user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    if u.username == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="admin 계정은 삭제할 수 없습니다.",
        )

    todo_store.delete_by_user(user_id)
    ok = user_store.delete(user_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="사용자 삭제에 실패했습니다.")
    return None


@router.get("/stats", response_model=AdminStatsOut)
def admin_stats(_: UserRecord = Depends(_require_admin)):
    users = user_store.list()
    total_users = len(users)
    total_todos = todo_store.count_all()
    done_todos = todo_store.count_done()
    done_rate = (done_todos / total_todos) if total_todos else 0.0
    return AdminStatsOut(
        total_users=total_users,
        total_todos=total_todos,
        done_todos=done_todos,
        done_rate=done_rate,
    )

