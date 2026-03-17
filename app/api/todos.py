import os
import re

import google.generativeai as genai
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.models.todo import TodoCreate, TodoOut, TodoUpdate
from app.store.sqlite import todo_store

router = APIRouter(prefix="/todos", tags=["todos"])


class TodoAiStepsIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class TodoAiStepsOut(BaseModel):
    title: str
    steps: list[str]


def _to_out(rec) -> TodoOut:
    # 내부 레코드를 API 응답 스키마로 변환
    return TodoOut(
        id=rec.id,
        title=rec.title,
        description=rec.description,
        done=rec.done,
        created_at=rec.created_at,
        updated_at=rec.updated_at,
    )


@router.get("", response_model=list[TodoOut])
def list_todos():
    # 전체 할 일 목록 조회
    return [_to_out(r) for r in todo_store.list()]


@router.post("", response_model=TodoOut, status_code=status.HTTP_201_CREATED)
def create_todo(payload: TodoCreate):
    # 할 일 생성
    rec = todo_store.create(title=payload.title, description=payload.description)
    return _to_out(rec)


@router.get("/{todo_id}", response_model=TodoOut)
def get_todo(todo_id: int):
    # 할 일 단건 조회
    rec = todo_store.get(todo_id)
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TODO not found")
    return _to_out(rec)


@router.patch("/{todo_id}", response_model=TodoOut)
def update_todo(todo_id: int, payload: TodoUpdate):
    # 할 일 부분 수정 (제목/설명/완료 여부)
    rec = todo_store.update(
        todo_id,
        title=payload.title,
        description=payload.description,
        done=payload.done,
    )
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TODO not found")
    return _to_out(rec)


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: int):
    # 할 일 삭제
    ok = todo_store.delete(todo_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TODO not found")
    return None


@router.post("/ai-steps", response_model=TodoAiStepsOut)
def generate_ai_steps(payload: TodoAiStepsIn):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GEMINI_API_KEY is not set",
        )

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = (
        "You are a helpful assistant for planning TODOs.\n"
        "Given a TODO title, generate 3 to 5 concrete, actionable execution steps.\n"
        "반드시 한국어로 답변해줘.\n"
        "답변은 JSON이나 마크다운 없이, 한 줄에 한 단계씩 순수 텍스트로만 적어줘. (번호나 불릿 기호 없이 문장만 한 줄에 하나씩)\n"
        f"TODO title: {payload.title!r}\n"
    )

    try:
        resp = model.generate_content(prompt)
        text = (getattr(resp, "text", None) or "").strip()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini request failed: {e}",
        )

    steps: list[str] = []
    lines = [ln.strip() for ln in re.split(r"\r?\n+", text) if ln.strip()]
    for ln in lines:
        ln = re.sub(r"^[-*•\s]+", "", ln)
        ln = re.sub(r"^\d+[.)]\s*", "", ln)
        ln = ln.strip()
        if ln:
            steps.append(ln)

    steps = [s for s in steps if s][:5]
    if len(steps) < 3:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gemini returned an unexpected format",
        )

    return TodoAiStepsOut(title=payload.title, steps=steps)

