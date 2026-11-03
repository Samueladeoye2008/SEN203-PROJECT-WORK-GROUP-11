"""Data layer: SQLAlchemy models (see docs/ARCHITECTURE.md for the ERD)."""
import secrets
from datetime import date, datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager

STATUSES = [("todo", "To do"), ("doing", "In progress"),
            ("review", "In review"), ("done", "Done")]
STATUS_KEYS = [s[0] for s in STATUSES]
PRIORITIES = ["low", "medium", "high"]
ROLE_LEADER, ROLE_MEMBER = "leader", "member"


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    matric_no = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    # Suspended users cannot log in. Super admin is set only by create_admin.py.
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_superadmin = db.Column(db.Boolean, nullable=False, default=False)
    memberships = db.relationship("Membership", back_populates="user",
                                  cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    user = db.session.get(User, int(user_id))
    return user if user and user.is_active else None   # suspended = logged out


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    join_code = db.Column(db.String(12), unique=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    memberships = db.relationship("Membership", back_populates="group",
                                  cascade="all, delete-orphan")
    tasks = db.relationship("Task", back_populates="group",
                            cascade="all, delete-orphan")

    @staticmethod
    def new_code():
        while True:
            code = secrets.token_hex(3).upper()
            if not Group.query.filter_by(join_code=code).first():
                return code

    @property
    def progress(self):
        """Percentage of tasks in 'done' (0 when there are no tasks)."""
        total = len(self.tasks)
        if not total:
            return 0
        return round(100 * sum(t.status == "done" for t in self.tasks) / total)


class Membership(db.Model):
    __table_args__ = (db.UniqueConstraint("user_id", "group_id"),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    role = db.Column(db.String(10), nullable=False, default=ROLE_MEMBER)
    user = db.relationship("User", back_populates="memberships")
    group = db.relationship("Group", back_populates="memberships")

    @property
    def is_leader(self):
        return self.role == ROLE_LEADER


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(500), default="")
    assigned_to = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    deadline = db.Column(db.Date)
    priority = db.Column(db.String(10), nullable=False, default="medium")
    status = db.Column(db.String(10), nullable=False, default="todo")
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    group = db.relationship("Group", back_populates="tasks")
    assignee = db.relationship("User", foreign_keys=[assigned_to])
    creator = db.relationship("User", foreign_keys=[created_by])

    @property
    def is_overdue(self):
        return bool(self.deadline and self.status != "done"
                    and self.deadline < date.today())


class ActivityLog(db.Model):
    """Audit trail: who did what and when (lecturer requirement)."""
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    task_id = db.Column(db.Integer)
    action = db.Column(db.String(30), nullable=False)
    detail = db.Column(db.String(200), default="")
    created_at = db.Column(db.DateTime, default=utcnow)
    user = db.relationship("User")


class Setting(db.Model):
    """Admin-editable limits (key/value). See app/limits.py for defaults."""
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(50), nullable=False)


class UsageCounter(db.Model):
    """Per-day usage counters, e.g. 'email:2026-11-02', 'writes:<uid>:2026-11-02'."""
    key = db.Column(db.String(80), primary_key=True)
    count = db.Column(db.Integer, nullable=False, default=0)
