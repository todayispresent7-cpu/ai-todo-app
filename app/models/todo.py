from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TodoCreate(BaseModel):
    # 클라이언트가 할 일을 "생성"할 때 보내는 데이터
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)


class TodoUpdate(BaseModel):
    # 클라이언트가 할 일을 "부분 수정(PATCH)"할 때 보내는 데이터
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    done: Optional[bool] = None


class TodoOut(BaseModel):
    # API가 응답으로 내려주는 할 일 데이터
    id: int
    title: str
    description: Optional[str] = None
    done: bool
    created_at: datetime
    updated_at: datetime

