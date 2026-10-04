from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.learning import router as learning_router
from app.core.config import settings
from app.db.session import check_database_connection

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend API for skill demand alignment and employment outcome tracking.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(learning_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "skillbridge-ai-api",
        "database": check_database_connection(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/health")
def health_check_v1() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "skillbridge-ai-api",
        "database": check_database_connection(),
        "version": settings.app_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "SkillBridge AI backend is running."}
