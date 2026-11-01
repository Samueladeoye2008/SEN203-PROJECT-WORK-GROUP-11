"""Create demo data: python seed.py  (password for all demo users: Password123)"""
from datetime import date, timedelta

from app import create_app
from app.extensions import db
from app.models import Group, Membership, Task, User

app = create_app()
with app.app_context():
    if User.query.first():
        raise SystemExit("Database already has data; delete app.db to reseed.")
    users = []
    for i, name in enumerate(["Demo Leader", "Demo Member A", "Demo Member B"], 1):
        u = User(name=name, matric_no=f"DEMO{i}", email=f"demo{i}@example.com")
        u.set_password("Password123")
        db.session.add(u)
        users.append(u)
    db.session.flush()
    g = Group(name="CSC GRP 11 Demo", join_code=Group.new_code(), created_by=users[0].id)
    db.session.add(g)
    db.session.flush()
    for i, u in enumerate(users):
        db.session.add(Membership(user_id=u.id, group_id=g.id,
                                  role="leader" if i == 0 else "member"))
    today = date.today()
    for title, who, days, status, prio in [
        ("Write SRS", 1, 3, "doing", "high"), ("Draw ERD", 2, 5, "todo", "medium"),
        ("Design wireframes", 2, -1, "todo", "high"), ("Set up Git repo", 0, -3, "done", "low")]:
        db.session.add(Task(group_id=g.id, title=title, assigned_to=users[who].id,
                            created_by=users[0].id, deadline=today + timedelta(days=days),
                            status=status, priority=prio))
    db.session.commit()
    print("Seeded. Log in with matric DEMO1 / Password123. Join code:", g.join_code)
