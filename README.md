# FastAPI 할 일 목록(TO-DO) REST API

간단한 **할 일 목록 CRUD REST API** 예제입니다.  
데이터베이스 없이 **메모리(in-memory)** 에 저장합니다(서버 재시작 시 초기화).

## 폴더 구조

```
e:\Vibe
├─ app
│  ├─ __init__.py
│  ├─ main.py
│  ├─ api
│  │  ├─ __init__.py
│  │  └─ todos.py
│  ├─ models
│  │  ├─ __init__.py
│  │  └─ todo.py
│  └─ store
│     ├─ __init__.py
│     └─ memory.py
├─ requirements.txt
└─ README.md
```

## 실행 방법 (Windows / PowerShell)

가상환경 생성/활성화:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

패키지 설치:

```powershell
pip install -r requirements.txt
```

Gemini API 키 설정(예: PowerShell):

```powershell
$env:GEMINI_API_KEY="여기에_본인_Gemini_API_키"
```

서버 실행:

```powershell
uvicorn app.main:app --reload
```

브라우저에서 문서 확인:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## API 요약

- `GET /health` : 헬스 체크
- `GET /todos` : 목록 조회
- `POST /todos` : 생성
- `GET /todos/{todo_id}` : 단건 조회
- `PATCH /todos/{todo_id}` : 부분 수정(완료 여부/제목/설명)
- `DELETE /todos/{todo_id}` : 삭제
- `POST /todos/ai-steps` : (Gemini) 제목으로 실행 단계 3~5개 자동 생성

