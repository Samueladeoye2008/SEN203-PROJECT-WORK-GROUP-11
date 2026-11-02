"""Email events: task assigned, task sent for review, daily deadline reminders."""
from datetime import date, timedelta

from flask import current_app, url_for
from flask_login import current_user

from .extensions import db
from .mailer import send_email
from .models import Membership, ROLE_LEADER, Task, User


def _board_link(group_id):
    return url_for("groups.board", group_id=group_id, _external=True)


def notify_assigned(task):
    if not task.assigned_to or task.assigned_to == current_user.id:
        return
    user = db.session.get(User, task.assigned_to)
    if not user:
        return
    due = task.deadline.strftime("%d %b %Y") if task.deadline else "none"
    body = (f"Hi {user.name},\n\n{current_user.name} assigned you a task in "
            f"{task.group.name}:\n\n{task.title}\nDeadline: {due}\n"
            f"Priority: {task.priority}\n\nOpen the board: {_board_link(task.group_id)}\n")
    send_email(current_app, user.email, f"New task: {task.title}", body)


def notify_review(task):
    """Tell the group leader(s) a task is waiting for review."""
    leaders = (Membership.query.filter_by(group_id=task.group_id, role=ROLE_LEADER).all())
    for m in leaders:
        if m.user_id == current_user.id:
            continue
        body = (f"Hi {m.user.name},\n\n{current_user.name} moved \"{task.title}\" to "
                f"In review in {task.group.name}.\n\nOpen the board: "
                f"{_board_link(task.group_id)}\n")
        send_email(current_app, m.user.email, f"Ready for review: {task.title}", body)


def send_reminders():
    """One digest per person for unfinished tasks overdue or due within 2 days."""
    today = date.today()
    tasks = Task.query.filter(Task.status != "done", Task.deadline.isnot(None),
                              Task.deadline <= today + timedelta(days=2),
                              Task.assigned_to.isnot(None)).all()
    by_user = {}
    for t in tasks:
        by_user.setdefault(t.assigned_to, []).append(t)
    sent = 0
    link = url_for("groups.dashboard", _external=True)
    for uid, items in by_user.items():
        user = db.session.get(User, uid)
        if not user:
            continue
        lines = [f"- {t.title} ({t.group.name}): "
                 f"{'OVERDUE, was due ' if t.deadline < today else 'due '}"
                 f"{t.deadline.strftime('%d %b %Y')}"
                 for t in sorted(items, key=lambda x: x.deadline)]
        body = (f"Hi {user.name},\n\nThese tasks need attention:\n\n" + "\n".join(lines)
                + f"\n\nOpen your boards: {link}\n")
        if send_email(current_app, user.email, "Task deadline reminder", body):
            sent += 1
    return sent
