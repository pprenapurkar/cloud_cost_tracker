"""Stage 4 — Persist the labelled DataFrame into a SQL database.

Falls back to a local SQLite file when Postgres env vars are absent,
so the pipeline runs even with zero external services.
"""
import os

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

TABLE = "cost_daily"


def get_engine(url: str | None = None) -> Engine:
    """Build a SQLAlchemy engine from an explicit url or env vars."""
    if url:
        return create_engine(url)
    host = os.getenv("POSTGRES_HOST")
    if host:
        user = os.getenv("POSTGRES_USER", "costint")
        pw = os.getenv("POSTGRES_PASSWORD", "")
        db = os.getenv("POSTGRES_DB", "costint")
        port = os.getenv("POSTGRES_PORT", "5432")
        return create_engine(
            f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}"
        )
    return create_engine("sqlite:///costint.db")


def persist(df: pd.DataFrame, engine: Engine | None = None) -> int:
    engine = engine or get_engine()
    df.to_sql(TABLE, engine, if_exists="replace", index=False)
    with engine.begin() as conn:
        conn.execute(text(
            f"CREATE INDEX IF NOT EXISTS idx_{TABLE}_date ON {TABLE} (date)"
        ))
    return len(df)
