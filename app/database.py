from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings
from app.db_url import is_postgres_url, is_sqlite_url, normalize_database_url


class Base(DeclarativeBase):
    pass


def _ensure_sqlite_dir(url: str) -> None:
    if url.startswith("sqlite:///"):
        path = Path(url.replace("sqlite:///", ""))
        path.parent.mkdir(parents=True, exist_ok=True)


def _build_engine():
    settings = get_settings()
    url = normalize_database_url(settings.database_url)
    _ensure_sqlite_dir(url)

    kwargs: dict = {}
    if is_sqlite_url(url):
        kwargs["connect_args"] = {"check_same_thread": False}
    elif is_postgres_url(url):
        kwargs["pool_pre_ping"] = True

    return create_engine(url, **kwargs)


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
