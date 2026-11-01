import pytest

from app import create_app
from app.extensions import db
from app.models import Group, Task
from config import TestConfig


@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.app_context():
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def register(c, matric, name="User", pw="Password123"):
    return c.post("/register", data=dict(name=name, matric_no=matric,
                  email=f"{matric}@x.com", password=pw, confirm=pw), follow_redirects=True)


def login(c, matric, pw="Password123"):
    return c.post("/login", data=dict(matric_no=matric, password=pw), follow_redirects=True)


def logout(c):
    c.post("/logout")


def setup_group(c):
    register(c, "A1", "Leader")
    c.post("/groups/create", data={"name": "G"})
    code = Group.query.first().join_code
    logout(c)
    register(c, "B1", "Member")
    c.post("/groups/join", data={"code": code})
    return code


def test_register_validation(client):
    r = client.post("/register", data=dict(name="", matric_no="", email="x",
                    password="short", confirm="no"), follow_redirects=True)
    assert b"Name is required" in r.data and b"at least 8" in r.data


def test_duplicate_matric_rejected(client):
    register(client, "A1")
    logout(client)
    assert b"already registered" in register(client, "A1").data


def test_login_wrong_password(client):
    register(client, "A1")
    logout(client)
    assert b"Wrong matric" in login(client, "A1", "badpassword1").data


def test_password_is_hashed(client):
    register(client, "A1")
    from app.models import User
    assert User.query.first().password_hash != "Password123"


def test_dashboard_requires_login(client):
    assert client.get("/dashboard").status_code == 302


def test_create_group_makes_leader(client):
    register(client, "A1")
    client.post("/groups/create", data={"name": "G"})
    g = Group.query.first()
    assert g.memberships[0].role == "leader"


def test_non_member_forbidden(client):
    setup_group(client)
    logout(client)
    register(client, "C1")
    assert client.get("/groups/1").status_code == 403


def test_task_lifecycle_and_progress(client):
    setup_group(client)
    logout(client)
    login(client, "A1")
    client.post("/groups/1/tasks", data=dict(title="T1", priority="high",
                deadline="2020-01-01", assigned_to="2"))
    t = Task.query.first()
    assert t.is_overdue and t.assigned_to == 2
    assert client.post(f"/tasks/{t.id}/move", json={"status": "done"}).status_code == 200
    assert Group.query.first().progress == 100
    assert not Task.query.first().is_overdue


def test_invalid_status_and_assignee(client):
    setup_group(client)
    logout(client)
    login(client, "A1")
    client.post("/groups/1/tasks", data=dict(title="T", priority="low"))
    assert client.post("/tasks/1/move", json={"status": "bogus"}).status_code == 400
    client.post("/groups/1/tasks", data=dict(title="Bad", priority="low", assigned_to="99"))
    assert Task.query.count() == 1


def test_member_cannot_move_others_task_or_delete(client):
    setup_group(client)
    logout(client)
    login(client, "A1")
    client.post("/groups/1/tasks", data=dict(title="Leader task", priority="low"))
    logout(client)
    login(client, "B1")
    assert client.post("/tasks/1/move", json={"status": "doing"}).status_code == 403
    client.post("/tasks/1/delete")
    assert Task.query.count() == 1


def test_member_can_move_assigned_task(client):
    setup_group(client)
    logout(client)
    login(client, "A1")
    client.post("/groups/1/tasks", data=dict(title="T", priority="low", assigned_to="2"))
    logout(client)
    login(client, "B1")
    assert client.post("/tasks/1/move", json={"status": "doing"}).status_code == 200


def test_activity_logged(client):
    setup_group(client)
    r = client.get("/groups/1/activity")
    assert b"member_joined" in r.data


def test_falls_back_to_sqlite_when_main_db_unreachable():
    class BadDb(TestConfig):
        SQLALCHEMY_DATABASE_URI = "postgresql://u:p@127.0.0.1:1/none"
        FALLBACK_DB_URI = "sqlite://"
    app = create_app(BadDb)
    assert app.config["DB_FALLBACK"] is True
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite://"
    assert b"temporary backup" in app.test_client().get("/login").data


def test_pages_render_with_data(client):
    setup_group(client)
    logout(client)
    login(client, "A1")
    client.post("/groups/1/tasks", data=dict(title="Render me", priority="high",
                deadline="2020-01-01", assigned_to="2"))
    board = client.get("/groups/1")
    assert board.status_code == 200 and b"Render me" in board.data and b"Overdue" in board.data
    assert client.get("/dashboard").status_code == 200
    assert client.get("/tasks/1/edit").status_code == 200
