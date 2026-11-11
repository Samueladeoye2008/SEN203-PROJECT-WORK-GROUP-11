"""Super admin: oversee users, groups, usage and limits. Read-only on boards."""
import secrets
from functools import wraps

from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, url_for)
from flask_login import current_user, login_required
from sqlalchemy import func

from .. import limits
from ..extensions import db
from ..mailer import config_problem, send_email_detailed
from ..models import ActivityLog, Group, Membership, Task, UsageCounter, User
from ..notifications import notify_reset

bp = Blueprint("admin", __name__, url_prefix="/admin")

FIELDS = [  # key, label, kind
    ("registration_open", "Registration open", "toggle"),
    ("max_users", "Maximum users", "num"),
    ("max_groups_per_user", "Groups one user may create", "num"),
    ("max_members_per_group", "Members per group", "num"),
    ("max_tasks_per_group", "Tasks per group", "num"),
    ("daily_writes_per_user", "Write requests per user per day", "num"),
    ("emails_enabled", "Email notifications on", "toggle"),
    ("daily_emails", "Emails per day (free Gmail is about 100)", "num"),
    ("storage_cap_mb", "Database storage cap (MB)", "num"),
]


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapper(*a, **kw):
        if not current_user.is_superadmin:
            abort(403)
        return view(*a, **kw)
    return wrapper


def _meter(label, used, cap, unit=""):
    pct = min(100, round(100 * used / cap)) if cap and used is not None else 0
    return dict(label=label, used=used, cap=cap, unit=unit, pct=pct)


@bp.route("/")
@admin_required
def dashboard():
    day = limits.today()
    writes = (db.session.query(func.coalesce(func.sum(UsageCounter.count), 0))
              .filter(UsageCounter.key.like(f"writes:%:{day}")).scalar())
    users, groups, tasks = User.query.count(), Group.query.count(), Task.query.count()
    meters = [
        _meter("Users", users, limits.get_limit("max_users")),
        _meter("Emails today", limits.count(f"email:{day}"), limits.get_limit("daily_emails")),
        _meter("Database size", limits.db_size_mb(), limits.get_limit("storage_cap_mb"), " MB"),
    ]
    stats = [("Users", users), ("Groups", groups), ("Tasks", tasks),
             ("Suspended", User.query.filter_by(is_active=False).count()),
             ("Write requests today", writes)]
    recent = ActivityLog.query.order_by(ActivityLog.id.desc()).limit(15).all()
    return render_template("admin/dashboard.html", stats=stats, meters=meters, recent=recent)


@bp.route("/users")
@admin_required
def users():
    q = request.args.get("q", "").strip()
    query = User.query
    if q:
        like = f"%{q}%"
        query = query.filter(User.name.ilike(like) | User.matric_no.ilike(like)
                             | User.email.ilike(like))
    return render_template("admin/users.html", users=query.order_by(User.id.desc()).limit(200).all(), q=q)


@bp.route("/users/<int:uid>/toggle", methods=["POST"])
@admin_required
def toggle_user(uid):
    user = db.get_or_404(User, uid)
    if user.id == current_user.id or user.is_superadmin:
        flash("You cannot suspend an administrator.", "error")
    else:
        user.is_active = not user.is_active
        db.session.commit()
        flash(f"{user.name} is now {'active' if user.is_active else 'suspended'}.", "message")
    return redirect(request.referrer or url_for("admin.users"))


@bp.route("/users/<int:uid>/reset", methods=["POST"])
@admin_required
def reset_password(uid):
    user = db.get_or_404(User, uid)
    if user.is_superadmin and user.id != current_user.id:
        flash("Reset another administrator's password with create_admin.py.", "error")
    else:
        temp = secrets.token_urlsafe(9)
        user.set_password(temp)
        db.session.commit()
        flash(f"Temporary password for {user.name}: {temp} (shown once; ask them to change it).", "message")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:uid>/reset-link", methods=["POST"])
@admin_required
def email_reset_link(uid):
    user = db.get_or_404(User, uid)
    if notify_reset(user):
        flash(f"Reset link emailed to {user.email}.", "message")
    else:
        flash("Could not send the email. Check Limits and email for the reason.", "error")
    return redirect(url_for("admin.users"))


@bp.route("/groups")
@admin_required
def groups():
    return render_template("admin/groups.html", groups=Group.query.order_by(Group.id.desc()).all())


@bp.route("/groups/<int:gid>/delete", methods=["POST"])
@admin_required
def delete_group(gid):
    group = db.get_or_404(Group, gid)
    name = group.name
    ActivityLog.query.filter_by(group_id=gid).delete()
    db.session.delete(group)                 # memberships and tasks cascade
    db.session.commit()
    flash(f"Deleted group {name}.", "message")
    return redirect(url_for("admin.groups"))


@bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    if request.method == "POST":
        name = " ".join(request.form.get("app_name", "").split())[:40]
        if name:
            limits.set_text("app_name", name)
        for key, _label, kind in FIELDS:
            if kind == "toggle":
                limits.set_limit(key, 1 if request.form.get(key) else 0)
            else:
                raw = request.form.get(key, "").strip()
                if raw.isdigit():
                    limits.set_limit(key, int(raw))
        flash("Settings saved.", "message")
        return redirect(url_for("admin.settings"))
    values = {k: limits.get_limit(k) for k, _l, _k in FIELDS}
    return render_template("admin/settings.html", fields=FIELDS, values=values,
                           name_value=limits.get_text("app_name", current_app.config["APP_NAME"]),
                           email_problem=config_problem(current_app))


@bp.route("/settings/test-email", methods=["POST"])
@admin_required
def test_email():
    ok, reason = send_email_detailed(current_app, current_user.email, "Test email",
                                     "If you can read this, the Apps Script email relay works.")
    flash("Test email sent. Check your inbox (and spam)." if ok else f"Email not sent: {reason}",
          "message" if ok else "error")
    return redirect(url_for("admin.settings"))


@bp.route("/users/<int:uid>/superadmin", methods=["POST"])
@admin_required
def toggle_superadmin(uid):
    user = db.get_or_404(User, uid)
    if user.id == current_user.id:
        flash("You cannot remove your own Super Admin access.", "error")
    else:
        user.is_superadmin = not user.is_superadmin
        db.session.commit()
        flash(f"{user.name} is now {'a Super Admin' if user.is_superadmin else 'a normal user'}.", "message")
    return redirect(url_for("admin.users"))
