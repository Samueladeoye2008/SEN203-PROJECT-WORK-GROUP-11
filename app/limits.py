"""Admin-controlled usage limits and daily counters. A cap of 0 means unlimited."""
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .extensions import db
from .models import Setting, UsageCounter

DEFAULTS = {
    "registration_open": 1,
    "max_users": 500,
    "max_groups_per_user": 5,
    "max_members_per_group": 15,
    "max_tasks_per_group": 200,
    "daily_writes_per_user": 1000,
    "emails_enabled": 1,
    "daily_emails": 90,
    "storage_cap_mb": 400,
}


def today():
    return datetime.now(timezone.utc).date().isoformat()


def get_limit(key):
    row = db.session.get(Setting, key)
    try:
        return int(row.value) if row else DEFAULTS[key]
    except ValueError:
        return DEFAULTS[key]


def get_text(key, default=""):
    row = db.session.get(Setting, key)
    return row.value if row and row.value else default


def set_text(key, value):
    value = str(value)[:50]
    row = db.session.get(Setting, key)
    if row:
        row.value = value
    else:
        db.session.add(Setting(key=key, value=value))
    db.session.commit()


def set_limit(key, value):
    row = db.session.get(Setting, key)
    if row:
        row.value = str(int(value))
    else:
        db.session.add(Setting(key=key, value=str(int(value))))
    db.session.commit()


def over(cap, used):
    """True when a positive cap has been reached."""
    return cap > 0 and used >= cap


def count(key):
    row = db.session.get(UsageCounter, key)
    return row.count if row else 0


def bump(key, by=1):
    for _ in range(2):                    # retry once if two requests create the row together
        try:
            row = db.session.get(UsageCounter, key)
            if not row:
                row = UsageCounter(key=key, count=0)
                db.session.add(row)
            row.count += by
            db.session.commit()
            return row.count
        except IntegrityError:
            db.session.rollback()
    return count(key)


def db_size_mb():
    """Database size in MB, or None if it cannot be measured."""
    try:
        dialect = db.engine.dialect.name
        if dialect == "postgresql":
            size = db.session.execute(text("SELECT pg_database_size(current_database())")).scalar()
        elif dialect == "sqlite":
            pages = db.session.execute(text("PRAGMA page_count")).scalar()
            psize = db.session.execute(text("PRAGMA page_size")).scalar()
            size = pages * psize
        else:
            return None
        return round(size / 1048576, 2)
    except Exception:
        db.session.rollback()
        return None


def storage_full():
    cap = get_limit("storage_cap_mb")
    size = db_size_mb()
    return bool(cap > 0 and size is not None and size >= cap)


STORAGE_MSG = "Storage limit reached. Please contact the administrator."
