import os
from dataclasses import dataclass, field


def _split_csv(value: str | None, default: str) -> list[str]:
    if not value:
        return [default]
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = "SkillBridge AI API"
    app_version: str = "0.3.0"
    app_env: str = os.getenv("APP_ENV", "development")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:////Users/aishwaryprataps219gmail.com/skillbridge-ai/backend/skillbridge_dev.db",
    )
    jwt_secret_key: str = os.getenv(
        "JWT_SECRET_KEY",
        "skillbridge-ai-development-secret-key-very-long-2025",
    )
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    cors_origins: list[str] = field(
        default_factory=lambda: _split_csv(
            os.getenv("CORS_ORIGINS"),
            "http://localhost:5173,http://localhost:5174",
        )
    )


settings = Settings()
