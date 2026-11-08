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
    assert app.config["DB_FALLBACK_REASON"]               # class name of the failure, no secrets
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


# ---------- email ----------
import json as _json
import app.mailer as mailer_mod
import app.notifications as notif_mod


@pytest.fixture
def mail_client():
    class MailConfig(TestConfig):
        APPS_SCRIPT_URL = "https://script.google.com/macros/s/x/exec"
        APPS_SCRIPT_SECRET = "s3cret"
        CRON_SECRET = "cron-s"
    app = create_app(MailConfig)
    with app.app_context():
        yield app.test_client()
        db.session.remove()
        db.drop_all()


@pytest.fixture
def sent(monkeypatch):
    calls = []
    monkeypatch.setattr(notif_mod, "send_email",
                        lambda app, to, subject, body, html=None: calls.append((to, subject, body, html)) or True)
    return calls


def test_send_email_disabled_without_config(client):
    from flask import current_app
    assert mailer_mod.send_email(current_app, "a@b.com", "s", "b") is False


def test_send_email_posts_secret_to_google_only(mail_client, monkeypatch):
    from flask import current_app
    seen = {}

    class Resp:
        def read(self): return b'{"ok": true}'
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake(req, timeout=0):
        seen["body"] = _json.loads(req.data)
        return Resp()
    monkeypatch.setattr(mailer_mod.urllib.request, "urlopen", fake)
    assert mailer_mod.send_email(current_app, "a@b.com", "Hi", "Body") is True
    assert seen["body"]["secret"] == "s3cret" and seen["body"]["to"] == "a@b.com"
    current_app.config["APPS_SCRIPT_URL"] = "https://evil.example.com/x"
    assert mailer_mod.send_email(current_app, "a@b.com", "Hi", "Body") is False


def test_assignment_emails_assignee_not_self(mail_client, sent):
    setup_group(mail_client)
    logout(mail_client)
    login(mail_client, "A1")
    mail_client.post("/groups/1/tasks", data=dict(title="T", priority="low", assigned_to="2"))
    assert [(c[0], c[1]) for c in sent if "Welcome" not in c[1]] == [("b1@x.com", "New task: T")]
    mail_client.post("/groups/1/tasks", data=dict(title="Mine", priority="low", assigned_to="1"))
    assert len([c for c in sent if "Welcome" not in c[1]]) == 1


def test_review_notifies_leader(mail_client, sent):
    setup_group(mail_client)
    logout(mail_client)
    login(mail_client, "A1")
    mail_client.post("/groups/1/tasks", data=dict(title="T", priority="low", assigned_to="2"))
    sent.clear()
    logout(mail_client)
    login(mail_client, "B1")
    mail_client.post("/tasks/1/move", json={"status": "review"})
    assert [(c[0], c[1]) for c in sent] == [("a1@x.com", "Ready for review: T")]


def test_quick_add_sets_status(mail_client):
    setup_group(mail_client)
    logout(mail_client)
    login(mail_client, "A1")
    mail_client.post("/groups/1/tasks", data=dict(title="T", priority="low", status="doing"))
    assert Task.query.first().status == "doing"


def test_cron_requires_secret_and_sends_digest(mail_client, sent):
    setup_group(mail_client)
    logout(mail_client)
    login(mail_client, "A1")
    mail_client.post("/groups/1/tasks", data=dict(title="Late", priority="low",
                     deadline="2020-01-01", assigned_to="2"))
    sent.clear()
    assert mail_client.get("/cron/reminders").status_code == 403
    r = mail_client.get("/cron/reminders", headers={"Authorization": "Bearer cron-s"})
    assert r.get_json() == {"sent": 1} and sent[0][0] == "b1@x.com"
    assert "<img" in sent[0][3]                          # branded HTML with logo


# ---------- super admin, limits, suspension ----------
from app.models import User
from app import limits as lim


def make_admin(matric="ADM", pw="AdminPass123"):
    u = User(name="Boss", matric_no=matric, email="boss@x.com", is_superadmin=True)
    u.set_password(pw)
    db.session.add(u)
    db.session.commit()


def test_admin_pages_forbidden_for_normal_user(client):
    register(client, "A1")
    for path in ("/admin/", "/admin/users", "/admin/groups", "/admin/settings"):
        assert client.get(path).status_code == 403


def test_admin_pages_open_for_super_admin(client):
    setup_group(client)
    logout(client)
    make_admin()
    login(client, "ADM", "AdminPass123")
    for path in ("/admin/", "/admin/users", "/admin/users?q=A1", "/admin/groups", "/admin/settings"):
        assert client.get(path).status_code == 200, path


def test_admin_views_board_read_only(client):
    setup_group(client)
    logout(client)
    make_admin()
    login(client, "ADM", "AdminPass123")
    r = client.get("/groups/1")
    assert r.status_code == 200 and b"Read-only administrator view" in r.data
    client.post("/groups/1/tasks", data=dict(title="Sneaky", priority="low"))
    assert Task.query.count() == 0                      # still 403 for writes


def test_suspend_blocks_login_and_session(client):
    register(client, "S1", "Sam")
    logout(client)
    make_admin()
    login(client, "ADM", "AdminPass123")
    uid = User.query.filter_by(matric_no="S1").first().id
    client.post(f"/admin/users/{uid}/toggle")
    logout(client)
    assert b"suspended" in login(client, "S1").data
    login(client, "ADM", "AdminPass123")
    client.post(f"/admin/users/{uid}/toggle")           # reactivate
    logout(client)
    assert b"Your boards" in login(client, "S1").data


def test_reset_password_and_settings_save(client):
    register(client, "S1", "Sam")
    logout(client)
    make_admin()
    login(client, "ADM", "AdminPass123")
    uid = User.query.filter_by(matric_no="S1").first().id
    assert b"Temporary password" in client.post(f"/admin/users/{uid}/reset", follow_redirects=True).data
    client.post("/admin/settings", data={"max_tasks_per_group": "3", "daily_emails": "7"})
    assert lim.get_limit("max_tasks_per_group") == 3 and lim.get_limit("daily_emails") == 7
    assert lim.get_limit("registration_open") == 0      # unchecked toggle saves as off


def test_task_and_group_limits_enforced(client):
    setup_group(client)
    logout(client)
    login(client, "A1")
    lim.set_limit("max_tasks_per_group", 1)
    client.post("/groups/1/tasks", data=dict(title="One", priority="low"))
    client.post("/groups/1/tasks", data=dict(title="Two", priority="low"))
    assert Task.query.count() == 1
    lim.set_limit("max_groups_per_user", 1)
    client.post("/groups/create", data={"name": "Second"})
    assert Group.query.count() == 1


def test_member_cap_and_registration_cap(client):
    register(client, "A1")
    client.post("/groups/create", data={"name": "G"})
    code = Group.query.first().join_code
    logout(client)
    lim.set_limit("max_members_per_group", 1)
    register(client, "B1")
    client.post("/groups/join", data={"code": code})
    assert len(Group.query.first().memberships) == 1
    logout(client)
    lim.set_limit("max_users", 2)
    assert b"user limit" in register(client, "C1").data


def test_daily_write_cap_returns_429_for_json(client):
    setup_group(client)
    logout(client)
    login(client, "A1")
    client.post("/groups/1/tasks", data=dict(title="T", priority="low"))
    lim.set_limit("daily_writes_per_user", 1)           # this user already used >1 writes today
    r = client.post("/tasks/1/move", json={"status": "done"})
    assert r.status_code == 429 and "limit" in r.get_json()["error"]


def test_email_daily_cap_blocks_sending(mail_client, monkeypatch):
    from flask import current_app

    class Resp:
        def read(self): return b'{"ok": true}'
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr(mailer_mod.urllib.request, "urlopen", lambda req, timeout=0: Resp())
    lim.set_limit("daily_emails", 1)
    assert mailer_mod.send_email(current_app, "a@b.com", "s", "b") is True
    assert mailer_mod.send_email(current_app, "a@b.com", "s", "b") is False
    lim.set_limit("daily_emails", 0)                     # 0 = unlimited
    assert mailer_mod.send_email(current_app, "a@b.com", "s", "b") is True


def test_change_password(client):
    register(client, "A1")
    client.post("/account", data=dict(current="Password123", new="NewPass1234", confirm="NewPass1234"))
    logout(client)
    assert b"Wrong matric" in login(client, "A1").data
    assert b"Your boards" in login(client, "A1", "NewPass1234").data


def test_storage_cap_blocks_creates(client, monkeypatch):
    register(client, "A1")
    monkeypatch.setattr(lim, "db_size_mb", lambda: 999.0)
    lim.set_limit("storage_cap_mb", 10)
    client.post("/groups/create", data={"name": "G"})
    assert Group.query.count() == 0


# ---------- landing page ----------
def test_landing_page_for_visitors(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"/register" in r.data and b"/login" in r.data and b"<svg" in r.data
    assert b"GroupFlow" in r.data                       # default app name


def test_signed_in_user_skips_landing(client):
    register(client, "A1")
    r = client.get("/")
    assert r.status_code == 302 and r.headers["Location"].endswith("/dashboard")


def test_app_name_is_configurable():
    class Named(TestConfig):
        APP_NAME = "MyBoard"
    app = create_app(Named)
    assert b"MyBoard" in app.test_client().get("/login").data


# ---------- email diagnostics ----------
def test_config_problem_messages(client):
    from flask import current_app
    assert ".env" in mailer_mod.config_problem(current_app)      # URL empty
    current_app.config["APPS_SCRIPT_URL"] = "https://script.google.com/macros/s/x/exec"
    assert "SECRET" in mailer_mod.config_problem(current_app)
    current_app.config["APPS_SCRIPT_SECRET"] = "s"
    assert mailer_mod.config_problem(current_app) == ""
    current_app.config["APPS_SCRIPT_URL"] = "https://example.com/x"
    assert "script.google.com" in mailer_mod.config_problem(current_app)


def test_detailed_reasons(mail_client, monkeypatch):
    from flask import current_app

    def reply(raw):
        class R:
            def read(self): return raw
            def __enter__(self): return self
            def __exit__(self, *a): return False
        monkeypatch.setattr(mailer_mod.urllib.request, "urlopen", lambda req, timeout=0: R())
    reply(b"<html>Sorry, unable to open the file</html>")
    assert "not return JSON" in mailer_mod.send_email_detailed(current_app, "a@b.com", "s", "b")[1]
    reply(b'{"ok": false, "error": "unauthorized"}')
    assert "SHARED_SECRET" in mailer_mod.send_email_detailed(current_app, "a@b.com", "s", "b")[1]
    reply(b'{"ok": true}')
    assert mailer_mod.send_email_detailed(current_app, "a@b.com", "s", "b") == (True, "sent")


def test_admin_settings_shows_email_problem(client):
    make_admin()
    login(client, "ADM", "AdminPass123")
    assert b"not configured" in client.get("/admin/settings").data



# ---------- welcome, forgot password, app name, logo ----------
import re as _re


def test_welcome_email_on_signup_without_password(client, sent):
    register(client, "W1", "Wale Ade")
    assert len(sent) == 1
    to, subject, body, html = sent[0]
    assert to == "w1@x.com" and "Welcome" in subject and "GroupFlow" in subject
    assert "Password123" not in body and "Password123" not in html       # never email passwords
    assert "W1" in body and "/login" in body and "logo.png" in html


def test_forgot_password_flow_single_use(mail_client, sent):
    client = mail_client
    register(client, "F1", "Fay")
    logout(client)
    sent.clear()
    r = client.post("/forgot", data={"email": "f1@x.com"})
    assert r.status_code == 302 and len(sent) == 1
    link = _re.search(r"/reset/[\w\-.]+", sent[0][2]).group(0)
    assert client.get(link).status_code == 200
    assert client.post(link, data={"new": "BrandNew123", "confirm": "BrandNew123"}).status_code == 302
    assert b"Your boards" in login(client, "F1", "BrandNew123").data
    logout(client)
    assert client.get(link).status_code == 302                          # used link no longer works


def test_forgot_password_unknown_email_and_daily_cap(mail_client, sent):
    client = mail_client
    register(client, "F1", "Fay")
    logout(client)
    sent.clear()
    r = client.post("/forgot", data={"email": "nobody@x.com"}, follow_redirects=True)
    assert b"If that email is registered" in r.data and sent == []      # same answer, no email
    for _ in range(5):
        client.post("/forgot", data={"email": "f1@x.com"})
    assert len(sent) == 3                                               # capped at 3 per day


def test_bad_reset_token_rejected(client):
    assert client.get("/reset/not-a-real-token").status_code == 302


def test_admin_emails_reset_link(client, sent):
    register(client, "S1", "Sam")
    logout(client)
    make_admin()
    login(client, "ADM", "AdminPass123")
    sent.clear()
    uid = User.query.filter_by(matric_no="S1").first().id
    client.post(f"/admin/users/{uid}/reset-link")
    assert len(sent) == 1 and "/reset/" in sent[0][2] and sent[0][0] == "s1@x.com"


def test_admin_can_rename_app(client):
    make_admin()
    login(client, "ADM", "AdminPass123")
    client.post("/admin/settings", data={"app_name": "  Task   Hub  "})
    assert b"Task Hub" in client.get("/admin/settings").data
    logout(client)
    assert b"Task Hub" in client.get("/").data and b"GroupFlow" not in client.get("/").data


def test_logo_served_and_used(client):
    assert client.get("/static/img/logo.svg").status_code == 200
    assert client.get("/static/img/logo.png").status_code == 200
    assert b"img/logo.svg" in client.get("/").data


def test_mailer_sends_html_field(mail_client, monkeypatch):
    from flask import current_app
    seen = {}

    class Resp:
        def read(self): return b'{"ok": true}'
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr(mailer_mod.urllib.request, "urlopen",
                        lambda req, timeout=0: seen.update(b=_json.loads(req.data)) or Resp())
    assert mailer_mod.send_email(current_app, "a@b.com", "s", "plain", "<p>hi</p>") is True
    assert seen["b"]["html"] == "<p>hi</p>" and seen["b"]["body"] == "plain"


def test_forgot_password_explains_when_email_not_set_up(client):
    r = client.post("/forgot", data={"email": "x@x.com"})
    assert r.status_code == 200 and b"Email is not set up" in r.data
