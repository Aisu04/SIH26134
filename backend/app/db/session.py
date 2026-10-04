from collections.abc import Generator

from sqlalchemy import create_engine, make_url, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings

if settings.database_url.startswith("sqlite") and make_url(settings.database_url).database in (
    None,
    "",
    ":memory:",
):
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        pool_pre_ping=True,
    )
elif settings.database_url.startswith("sqlite"):
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
else:
    engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> str:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "connected"
    except Exception as exc:  # pragma: no cover - runtime validation only
        return f"unavailable: {exc.__class__.__name__}"
