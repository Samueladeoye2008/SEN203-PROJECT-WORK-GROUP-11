from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import (ActivityLog, Group, Membership, ROLE_LEADER, ROLE_MEMBER,
                      STATUSES, Task)
from .. import limits
from ..utils import log_activity, membership_or_403, view_membership_or_403, leader_or_403

bp = Blueprint("groups", __name__)


@bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", memberships=current_user.memberships, today=date.today())


@bp.route("/groups/create", methods=["POST"])
@login_required
def create():
    name = request.form.get("name", "").strip()
    if not name or len(name) > 100:
        flash("Enter a group name (max 100 characters).", "error")
        return redirect(url_for("groups.dashboard"))
    if limits.over(limits.get_limit("max_groups_per_user"),
                   Group.query.filter_by(created_by=current_user.id).count()):
        flash("You have reached the maximum number of groups you can create.", "error")
        return redirect(url_for("groups.dashboard"))
    if limits.storage_full():
        flash(limits.STORAGE_MSG, "error")
        return redirect(url_for("groups.dashboard"))
    group = Group(name=name, join_code=Group.new_code(), created_by=current_user.id)
    db.session.add(group)
    db.session.flush()
    db.session.add(Membership(user_id=current_user.id, group_id=group.id,
                              role=ROLE_LEADER))
    log_activity(group.id, "group_created", name)
    db.session.commit()
    return redirect(url_for("groups.board", group_id=group.id))


@bp.route("/groups/join", methods=["POST"])
@login_required
def join():
    code = request.form.get("code", "").strip().upper()
    group = Group.query.filter_by(join_code=code).first()
    if not group:
        flash("No group found with that code.", "error")
        return redirect(url_for("groups.dashboard"))
    if Membership.query.filter_by(user_id=current_user.id, group_id=group.id).first():
        flash("You are already in that group.", "error")
        return redirect(url_for("groups.board", group_id=group.id))
    if limits.over(limits.get_limit("max_members_per_group"), len(group.memberships)):
        flash("That group is full.", "error")
        return redirect(url_for("groups.dashboard"))
    db.session.add(Membership(user_id=current_user.id, group_id=group.id,
                              role=ROLE_MEMBER))
    log_activity(group.id, "member_joined", current_user.name)
    db.session.commit()
    return redirect(url_for("groups.board", group_id=group.id))


@bp.route("/groups/<int:group_id>")
@login_required
def board(group_id):
    me = view_membership_or_403(group_id)
    group = db.get_or_404(Group, group_id)
    far = date.max
    tasks = sorted(group.tasks, key=lambda t: (t.deadline or far, t.id))
    columns = [(key, label, [t for t in tasks if t.status == key])
               for key, label in STATUSES]
    return render_template("board.html", group=group, me=me, columns=columns,
                           members=group.memberships, statuses=STATUSES,
                           today=date.today())


@bp.route("/groups/<int:group_id>/activity")
@login_required
def activity(group_id):
    view_membership_or_403(group_id)
    group = db.get_or_404(Group, group_id)
    logs = (ActivityLog.query.filter_by(group_id=group_id)
            .order_by(ActivityLog.id.desc()).limit(100).all())
    return render_template("activity.html", group=group, logs=logs)


@bp.route("/groups/<int:group_id>/members/<int:user_id>/role", methods=["POST"])
@login_required
def change_role(group_id, user_id):
    leader_or_403(group_id)
    target = Membership.query.filter_by(user_id=user_id, group_id=group_id).first()
    if not target:
        flash("That user is not a member of this board.", "error")
        return redirect(url_for("groups.board", group_id=group_id))
    role = request.form.get("role", ROLE_MEMBER)
    if role not in (ROLE_LEADER, ROLE_MEMBER):
        flash("Invalid role.", "error")
        return redirect(url_for("groups.board", group_id=group_id))
    if target.user_id == current_user.id and role == ROLE_MEMBER:
        leaders = Membership.query.filter_by(group_id=group_id, role=ROLE_LEADER).count()
        if leaders <= 1:
            flash("A board must always have at least one Team Leader. Promote another member first.", "error")
            return redirect(url_for("groups.board", group_id=group_id))
    if target.role != role:
        old = target.role
        target.role = role
        log_activity(group_id, "role_changed", f"{target.user.name}: {old} -> {role}")
        db.session.commit()
        flash(f"{target.user.name} is now a {'Team Leader' if role == ROLE_LEADER else 'Member'}.", "message")
    return redirect(url_for("groups.board", group_id=group_id))


@bp.route("/groups/<int:group_id>/members/<int:user_id>/remove", methods=["POST"])
@login_required
def remove_member(group_id, user_id):
    leader_or_403(group_id)
    target = Membership.query.filter_by(user_id=user_id, group_id=group_id).first()
    if not target:
        flash("That user is not a member of this board.", "error")
        return redirect(url_for("groups.board", group_id=group_id))
    if target.user_id == current_user.id:
        leaders = Membership.query.filter_by(group_id=group_id, role=ROLE_LEADER).count()
        if leaders <= 1:
            flash("You cannot leave as the only Team Leader. Promote another leader first.", "error")
            return redirect(url_for("groups.board", group_id=group_id))
    name = target.user.name
    db.session.delete(target)
    log_activity(group_id, "member_removed", name)
    db.session.commit()
    flash(f"{name} was removed from the board.", "message")
    return redirect(url_for("groups.board", group_id=group_id))
