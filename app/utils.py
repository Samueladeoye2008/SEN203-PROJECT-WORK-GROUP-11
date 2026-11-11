"""Shared helpers: authorization and activity logging."""
from datetime import datetime
from types import SimpleNamespace

from flask import abort
from flask_login import current_user

from .extensions import db
from .models import ActivityLog, Membership, ROLE_LEADER


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


def view_membership_or_403(group_id):
    """Members get their membership; super admins get a read-only observer view."""
    m = Membership.query.filter_by(user_id=current_user.id, group_id=group_id).first()
    if m:
        return m
    if current_user.is_superadmin:
        return SimpleNamespace(is_leader=False, read_only=True, user_id=current_user.id)
    abort(403)


def leader_or_403(group_id):
    """Require current user to be a leader of the group."""
    m = membership_or_403(group_id)
    if not m.is_leader:
        abort(403)
    return m
