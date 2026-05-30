"""Normalize DATABASE_URL for SQLAlchemy (SQLite local, Neon PostgreSQL in production)."""


def normalize_database_url(url: str) -> str:
    """Map Neon-style URLs to SQLAlchemy + psycopg3 driver."""
    raw = url.strip()
    if not raw:
        return raw
    if raw.startswith("postgres://"):
        return "postgresql+psycopg://" + raw[len("postgres://") :]
    if raw.startswith("postgresql://") and "+psycopg" not in raw:
        return "postgresql+psycopg://" + raw[len("postgresql://") :]
    return raw


def is_sqlite_url(url: str) -> bool:
    return url.startswith("sqlite:")


def is_postgres_url(url: str) -> bool:
    return url.startswith("postgresql")
