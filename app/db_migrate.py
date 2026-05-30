"""Lightweight schema migrations for SQLite and PostgreSQL (e.g. Neon)."""

import logging

from sqlalchemy import inspect, text

from app.database import engine
from app.db_url import is_postgres_url

logger = logging.getLogger(__name__)


def _add_column(conn, table: str, column: str, ddl: str) -> None:
    conn.execute(text(ddl))
    logger.info("Added %s.%s column", table, column)


def run_migrations() -> None:
    insp = inspect(engine)
    if not insp.has_table("events"):
        return

    cols = {c["name"] for c in insp.get_columns("events")}
    pg = is_postgres_url(str(engine.url))

    with engine.begin() as conn:
        if "origin" not in cols:
            if pg:
                _add_column(
                    conn,
                    "events",
                    "origin",
                    "ALTER TABLE events ADD COLUMN IF NOT EXISTS origin VARCHAR(16) DEFAULT 'pipeline'",
                )
            else:
                _add_column(
                    conn,
                    "events",
                    "origin",
                    "ALTER TABLE events ADD COLUMN origin VARCHAR(16) DEFAULT 'pipeline'",
                )
        if "agent_run_id" not in cols:
            if pg:
                _add_column(
                    conn,
                    "events",
                    "agent_run_id",
                    "ALTER TABLE events ADD COLUMN IF NOT EXISTS agent_run_id INTEGER",
                )
            else:
                _add_column(
                    conn,
                    "events",
                    "agent_run_id",
                    "ALTER TABLE events ADD COLUMN agent_run_id INTEGER",
                )

    from app.database import init_db
    from app import models  # noqa: F401

    init_db()
    if not insp.has_table("demo_quotas"):
        logger.info("Ensured demo_quotas table exists")
