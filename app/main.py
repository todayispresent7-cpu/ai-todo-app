from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.todos import router as todos_router
from pathlib import Path


def create_app() -> FastAPI:
    # FastAPI 앱 생성 (제목/설명은 문서에 표시됩니다)
    app = FastAPI(
        title="할 일 목록(TO-DO) REST API",
        description="FastAPI로 만든 간단한 할 일 목록 CRUD API 예제입니다.",
        version="1.0.0",
    )

    # 정적 파일(file://)에서 접근하는 순수 프론트엔드를 위해 CORS 허용
    # 운영 환경에서는 허용 Origin을 명시적으로 제한하세요.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 간단한 헬스 체크 엔드포인트
    @app.get("/health")
    def health():
        # 운영 환경에서는 DB 연결 상태 등을 함께 점검할 수 있습니다.
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    def index():
        project_root = Path(__file__).resolve().parents[1]
        index_path = project_root / "index.html"
        if not index_path.is_file():
            raise HTTPException(
                status_code=404,
                detail=f"index.html not found at {index_path}",
            )
        return FileResponse(index_path)

    # 라우터 등록
    app.include_router(todos_router)
    return app


app = create_app()

