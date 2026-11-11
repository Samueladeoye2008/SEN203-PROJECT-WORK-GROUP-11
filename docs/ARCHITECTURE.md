# Architecture and Design: CSC GRP 11 Task Board

Process model: Incremental. Stack: Python Flask, SQLite (SQLAlchemy), Jinja templates, vanilla JS.

## 1. Architecture (layered MVC, Flask blueprints)

```
Browser (HTML + CSS + board.js)
        |  HTTP / JSON (fetch, CSRF token)
Presentation   templates/*.html, static/
Controllers    auth/routes.py, groups/routes.py, tasks/routes.py   (blueprints)
Business rules utils.py (membership checks, activity log), validation in routes
Data access    models.py (SQLAlchemy ORM)
Storage        SQLite file app.db
```
Why: modular (one blueprint per feature), low coupling (routes depend on models, never on each other), high cohesion (each module has one job). The app factory (`create_app`) lets tests use an in-memory database.

## 2. Modules and increments

| Increment | Module | Files |
|---|---|---|
| 1 | Accounts | auth/routes.py, login.html, register.html |
| 1 | Groups | groups/routes.py, dashboard.html |
| 2 | Tasks + Kanban | tasks/routes.py, board.html, board.js |
| 3 | Deadlines, progress, activity log | Task.is_overdue, Group.progress, activity.html |

## 3. ERD

```mermaid
erDiagram
    USER ||--o{ MEMBERSHIP : has
    GROUP ||--o{ MEMBERSHIP : has
    GROUP ||--o{ TASK : contains
    USER ||--o{ TASK : "assigned to"
    USER ||--o{ TASK : creates
    GROUP ||--o{ ACTIVITY_LOG : records
    USER ||--o{ ACTIVITY_LOG : performs
    USER {
        int id PK
        string name
        string matric_no UK
        string email UK
        string password_hash
    }
    GROUP {
        int id PK
        string name
        string join_code UK
        int created_by FK
    }
    MEMBERSHIP {
        int id PK
        int user_id FK
        int group_id FK
        string role
    }
    TASK {
        int id PK
        int group_id FK
        string title
        string description
        int assigned_to FK
        int created_by FK
        date deadline
        string priority
        string status
    }
    ACTIVITY_LOG {
        int id PK
        int group_id FK
        int user_id FK
        int task_id
        string action
        string detail
        datetime created_at
    }
```
User and Group are many-to-many, resolved by MEMBERSHIP (carries the role). Unique constraint on (user_id, group_id).

## 4. Roles and permissions

The system uses two levels of authorization:

- **System level:** Super Admin controls system-wide users, groups, limits and email settings.
- **Board level:** every membership is either **Team Leader** or **Member**. A user can have different roles on different boards.

| Action | Super Admin | Team Leader | Member | Non-member |
|---|---|---|---|---|
| View board/activity | Read-only | Yes | Yes | No |
| Create a board | Yes | Yes | Yes | No |
| Join a board by code | Yes | Yes | Yes | No |
| Create task | Read-only | Yes | Yes | No |
| Assign task to another member | Read-only | Yes | No (self only) | No |
| Edit/move own task | Read-only | Yes | Yes | No |
| Delete task | Read-only | Yes | No | No |
| Promote/demote board members | Read-only | Yes | No | No |
| Remove board members | Read-only | Yes | No | No |
| Manage users/system settings | Yes | No | No | No |

A board must always have at least one Team Leader. Super Admins can be granted or removed only by another Super Admin; a Super Admin cannot remove their own access.

## 5. Use cases
(for the UI/UX and Design leads)
Register, Log in, Create group, Join group by code, Add task, Assign task, Edit task, Move task (drag or arrows), Delete task (leader), View progress, View activity log, Log out.

## 6. Key routes

| Method | Route | Purpose |
|---|---|---|
| GET/POST | /register, /login | Accounts |
| POST | /logout | End session |
| GET | /dashboard | My groups |
| POST | /groups/create, /groups/join | Group management |
| GET | /groups/<id>, /groups/<id>/activity | Board, history |
| POST | /groups/<id>/tasks | Create task |
| POST | /groups/<id>/members/<user_id>/role | Change board role (leader only) |
| POST | /groups/<id>/members/<user_id>/remove | Remove board member (leader only) |
| GET/POST | /tasks/<id>/edit | Edit task |
| POST (JSON) | /tasks/<id>/move | Change status |
| POST | /tasks/<id>/delete | Delete task |

## 7. Non-functional design decisions

| Requirement | How it is met |
|---|---|
| Security | Hashed passwords (werkzeug), CSRF tokens on all POSTs, ORM prevents SQL injection, Jinja auto-escaping prevents XSS, server-side role checks, open-redirect guard on login |
| Usability | Responsive CSS, arrow buttons as well as drag-and-drop (works on phones) |
| Maintainability | Blueprints, app factory, comments, tests |
| Accountability | Activity log of every change with user and time |
| Portability | SQLite file; switch DB by setting `DATABASE_URL` |

## 8. Known limitations (state these in the defense)
SQLite suits light concurrent use only; no email notifications yet (Increment 3 extension); no password reset; leader role cannot be transferred; times are stored in UTC.
