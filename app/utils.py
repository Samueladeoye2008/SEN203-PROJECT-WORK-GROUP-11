"""Shared helpers: authorization and activity logging."""
from datetime import datetime

from flask import abort
from flask_login import current_user

from .extensions import db
from .models import ActivityLog, Membership


def membership_or_403(group_id):
    m = Membership.query.filter_by(user_id=current_user.id,
                                   group_id=group_id).first()
    if not m:
        abort(403)
    return m


def log_activity(group_id, action, detail="", task_id=None):
    db.session.add(ActivityLog(group_id=group_id, user_id=current_user.id,
                               task_id=task_id, action=action,
                               detail=detail[:200]))


def parse_date(value):
    """Return a date from 'YYYY-MM-DD', None if blank, ValueError if bad."""
    value = (value or "").strip()
    return datetime.strptime(value, "%Y-%m-%d").date() if value else None
