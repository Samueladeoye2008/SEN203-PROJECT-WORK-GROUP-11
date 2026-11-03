"""Tiny auto-migration: add new columns to tables created by an older version."""
from sqlalchemy import inspect, text

from .extensions import db

ADDITIONS = {"user": [("is_active", "BOOLEAN NOT NULL DEFAULT {t}"),
                      ("is_superadmin", "BOOLEAN NOT NULL DEFAULT {f}")]}


def ensure_columns():
    pg = db.engine.dialect.name == "postgresql"
    t, f = ("TRUE", "FALSE") if pg else ("1", "0")
    insp = inspect(db.engine)
    for table, cols in ADDITIONS.items():
        existing = {c["name"] for c in insp.get_columns(table)}
        for name, ddl in cols:
            if name not in existing:
                db.session.execute(text(
                    f'ALTER TABLE "{table}" ADD COLUMN {name} {ddl.format(t=t, f=f)}'))
    db.session.commit()
