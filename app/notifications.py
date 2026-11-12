"""Email events: task assigned, task sent for review, daily deadline reminders."""
from datetime import date, timedelta

from flask import current_app, url_for
from flask_login import current_user

from .branding import app_name
from .emails import build_html
from .extensions import db
from .mailer import send_email
from .models import Membership, ROLE_LEADER, Task, User
from .tokens import make_reset_token


def _send(to, subject, heading, paragraphs, button=None):
    """Send a branded email: plain text plus HTML with the logo."""
    logo = url_for("static", filename="img/logo.png", _external=True)
    text = "\n\n".join(paragraphs)
    if button:
        text += f"\n\n{button[0]}: {button[1]}"
    html = build_html(app_name(), logo, heading, paragraphs, button)
    return send_email(current_app, to, subject, text, html)


def notify_welcome(user):
    name = app_name()
    return _send(user.email, f"Welcome to {name}", f"Welcome to {name}, {user.name.split()[0]}!",
                 ["Your account is ready.",
                  f"Log in with your matric number: {user.matric_no} and the password you chose.",
                  "Ask your group leader for a join code to join a board, or create a new board yourself."],
                 ("Log in", url_for("auth.login", _external=True)))


def notify_reset(user):
    link = url_for("auth.reset_password", token=make_reset_token(user), _external=True)
    return _send(user.email, "Reset your password", "Reset your password",
                 [f"Hi {user.name.split()[0]}, we received a request to reset your password.",
                  "This link works once and expires in 1 hour. If you did not ask for it, ignore this email."],
                 ("Choose a new password", link))


def _board_link(group_id):
    return url_for("groups.board", group_id=group_id, _external=True)


def notify_assigned(task):
    if not task.assigned_to or task.assigned_to == current_user.id:
        return
    user = db.session.get(User, task.assigned_to)
    if not user:
        return
    due = task.deadline.strftime("%d %b %Y") if task.deadline else "none"
    _send(user.email, f"New task: {task.title}", "You have a new task",
          [f"Hi {user.name.split()[0]}, {current_user.name} assigned you a task in {task.group.name}.",
           f"Task: {task.title}", f"Deadline: {due}. Priority: {task.priority}."],
          ("Open the board", _board_link(task.group_id)))



def notify_task_created(task):
    """Tell every current group member that a new task was created."""
    due = task.deadline.strftime("%d %b %Y") if task.deadline else "No deadline"
    assigned = task.assignee.name if task.assignee else "Unassigned"
    sent = 0
    members = Membership.query.filter_by(group_id=task.group_id).all()
    for m in members:
        if not m.user or not m.user.email:
            continue
        if _send(
            m.user.email,
            f"New task created: {task.title}",
            "A new task was created",
            [
                f"Hi {m.user.name.split()[0]}, a new task was created in {task.group.name}.",
                f"Task: {task.title}",
                f"Description: {task.description or 'No description provided.'}",
                f"Priority: {task.priority.capitalize()}",
                f"Deadline: {due}",
                f"Assigned to: {assigned}",
                f"Created by: {task.creator.name if task.creator else current_user.name}",
            ],
            ("Open the board", _board_link(task.group_id)),
        ):
            sent += 1
    return sent


def notify_group_joined(user, group):
    """Tell the new member and existing members that someone joined a group."""
    sent = 0
    _send(
        user.email,
        f"You joined {group.name}",
        "You joined a project group",
        [
            f"Hi {user.name.split()[0]}, you have successfully joined {group.name}.",
            f"Group join code: {group.join_code}",
            "You can now access the board and work on tasks available to you.",
        ],
        ("Open the board", _board_link(group.id)),
    )
    for m in Membership.query.filter_by(group_id=group.id).all():
        if not m.user or m.user_id == user.id or not m.user.email:
            continue
        if _send(
            m.user.email,
            f"New member joined {group.name}",
            "A new member joined your group",
            [
                f"Hi {m.user.name.split()[0]}, {user.name} has joined {group.name}.",
                "They can now access the project board according to their role.",
            ],
            ("Open the board", _board_link(group.id)),
        ):
            sent += 1
    return sent


def notify_group_invite(email, group, inviter):
    """Send a join-code invitation to an email address."""
    return _send(
        email,
        f"You are invited to {group.name}",
        "You are invited to a StudentBoard group",
        [
            f"{inviter.name} invited you to join {group.name}.",
            f"Join code: {group.join_code}",
            "Create an account or log in to StudentBoard, then use this code from the dashboard to join the group.",
        ],
        ("Open StudentBoard", url_for("auth.login", _external=True)),
    )

def notify_review(task):
    """Tell the group leader(s) a task is waiting for review."""
    leaders = (Membership.query.filter_by(group_id=task.group_id, role=ROLE_LEADER).all())
    for m in leaders:
        if m.user_id == current_user.id:
            continue
        _send(m.user.email, f"Ready for review: {task.title}", "A task is ready for review",
              [f"Hi {m.user.name.split()[0]}, {current_user.name} moved \"{task.title}\" to In review "
               f"in {task.group.name}."],
              ("Open the board", _board_link(task.group_id)))


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
        if _send(user.email, "Task deadline reminder", "Tasks that need attention",
                 [f"Hi {user.name.split()[0]}, these tasks are overdue or due soon:"] + lines,
                 ("Open your boards", link)):
            sent += 1
    return sent
