from flask import (Blueprint, current_app, flash, jsonify, redirect,
                   render_template, request, url_for)
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Membership, PRIORITIES, STATUS_KEYS, Task
from ..notifications import notify_assigned, notify_review
from ..utils import log_activity, membership_or_403, parse_date

bp = Blueprint("tasks", __name__)


def _can_modify(task, me):
    """Leader, assignee, or creator may change a task."""
    return me.is_leader or task.assigned_to == current_user.id \
        or task.created_by == current_user.id


def _validated(form, group_id, me):
    """Return (values, errors) for task create/edit forms."""
    errors, vals = [], {}
    title = form.get("title", "").strip()
    if not title or len(title) > 120:
        errors.append("Title is required (max 120 characters).")
    vals["title"] = title
    vals["description"] = form.get("description", "").strip()[:500]
    prio = form.get("priority", "medium")
    if prio not in PRIORITIES:
        errors.append("Invalid priority.")
    vals["priority"] = prio
    try:
        vals["deadline"] = parse_date(form.get("deadline"))
    except ValueError:
        errors.append("Deadline must be a valid date.")
    assignee = form.get("assigned_to", "")
    if assignee:
        ok = assignee.isdigit() and Membership.query.filter_by(
            user_id=int(assignee), group_id=group_id).first()
        if not ok:
            errors.append("Assignee must be a member of this group.")
        vals["assigned_to"] = int(assignee) if ok else None
    else:
        vals["assigned_to"] = None
    return vals, errors


@bp.route("/groups/<int:group_id>/tasks", methods=["POST"])
@login_required
def create(group_id):
    me = membership_or_403(group_id)
    if not (me.is_leader or current_app.config["ANY_MEMBER_CAN_CREATE"]):
        flash("Only the group leader can create tasks.", "error")
        return redirect(url_for("groups.board", group_id=group_id))
    vals, errors = _validated(request.form, group_id, me)
    if not me.is_leader:               # members cannot assign to others
        vals["assigned_to"] = vals.get("assigned_to") if vals.get("assigned_to") == current_user.id else None
    if errors:
        for e in errors:
            flash(e, "error")
    else:
        status = request.form.get("status", "todo")
        if status not in STATUS_KEYS:
            status = "todo"
        task = Task(group_id=group_id, created_by=current_user.id, status=status, **vals)
        db.session.add(task)
        db.session.flush()
        log_activity(group_id, "task_created", task.title, task.id)
        db.session.commit()
        notify_assigned(task)
    return redirect(url_for("groups.board", group_id=group_id))


@bp.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit(task_id):
    task = db.get_or_404(Task, task_id)
    me = membership_or_403(task.group_id)
    if not _can_modify(task, me):
        flash("You cannot edit this task.", "error")
        return redirect(url_for("groups.board", group_id=task.group_id))
    if request.method == "POST":
        vals, errors = _validated(request.form, task.group_id, me)
        if not me.is_leader:           # only leader may reassign
            vals["assigned_to"] = task.assigned_to
        old_assignee = task.assigned_to
        status = request.form.get("status", task.status)
        if status not in STATUS_KEYS:
            errors.append("Invalid status.")
        if errors:
            for e in errors:
                flash(e, "error")
        else:
            for k, v in vals.items():
                setattr(task, k, v)
            task.status = status
            log_activity(task.group_id, "task_edited", task.title, task.id)
            db.session.commit()
            if task.assigned_to != old_assignee:
                notify_assigned(task)
            return redirect(url_for("groups.board", group_id=task.group_id))
    return render_template("task_edit.html", task=task, me=me,
                           members=task.group.memberships)


@bp.route("/tasks/<int:task_id>/move", methods=["POST"])
@login_required
def move(task_id):
    task = db.get_or_404(Task, task_id)
    me = membership_or_403(task.group_id)
    status = (request.get_json(silent=True) or {}).get("status")
    if status not in STATUS_KEYS:
        return jsonify(error="Invalid status."), 400
    if not _can_modify(task, me):
        return jsonify(error="Only the assignee, creator or leader can move this task."), 403
    if task.status != status:
        old, task.status = task.status, status
        log_activity(task.group_id, "task_moved", f"{task.title}: {old} -> {status}", task.id)
        db.session.commit()
        if status == "review":
            notify_review(task)
    return jsonify(ok=True, status=task.status)


@bp.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def delete(task_id):
    task = db.get_or_404(Task, task_id)
    me = membership_or_403(task.group_id)
    if not me.is_leader:
        flash("Only the group leader can delete tasks.", "error")
    else:
        log_activity(task.group_id, "task_deleted", task.title, task.id)
        db.session.delete(task)
        db.session.commit()
    return redirect(url_for("groups.board", group_id=task.group_id))
