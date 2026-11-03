# CSC GRP 11: Group Project Task Board

A Kanban board where student groups assign tasks, set deadlines, and track progress.
Python Flask, SQLAlchemy, Tailwind CSS, SQLite (local) / PostgreSQL on Neon (hosted).
Process model: Incremental. Full design notes: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Features
- Welcome email on signup, forgot-password by email (single-use link, 1 hour), admin can email a reset link
- Admin-editable app name (default GroupFlow) and logo in header, landing page, favicon and emails
- Landing page for visitors (what Kanban is, how it works, sign up and log in buttons)
- Register and log in with matric number
- Create a group, join with a code, leader and member roles
- Kanban board (To do, In progress, In review, Done) with drag and drop and arrow buttons
- Task assignee, deadline, priority, overdue and due-soon highlighting
- Progress bar, task counts, "only my tasks" filter
- Activity log of every change (who, what, when)
- Responsive, dark-mode aware UI

## Architecture

```mermaid
flowchart LR
    B["Browser<br/>Tailwind UI + board.js"] -->|"HTTP and JSON + CSRF token"| C
    subgraph F["Flask app (create_app)"]
        C["Blueprints<br/>auth, groups, tasks"] --> U["utils.py<br/>permissions, activity log"]
        C --> M["models.py<br/>SQLAlchemy ORM"]
        U --> M
        C --> T["Jinja templates"]
    end
    T --> B
    M --> S{"db_select.py"}
    S -->|"DATABASE_URL reachable"| N[("Neon PostgreSQL")]
    S -->|"local run or fallback"| Q[("SQLite")]
```

## Project structure

```mermaid
flowchart TD
    R["taskboard/"] --> IDX["index.py<br/>Vercel entrypoint"]
    R --> RUN["run.py<br/>local server"]
    R --> CFG["config.py<br/>settings"]
    R --> SEED["seed.py<br/>demo data"]
    R --> APP["app/"]
    R --> PUB["public/static/<br/>css, js"]
    R --> TST["tests/<br/>pytest"]
    R --> DOC["docs/<br/>ARCHITECTURE.md"]
    APP --> INIT["__init__.py<br/>app factory"]
    APP --> MOD["models.py"]
    APP --> UT["utils.py"]
    APP --> DBS["db_select.py"]
    APP --> AU["auth/<br/>login, register"]
    APP --> GR["groups/<br/>dashboard, board, activity"]
    APP --> TK["tasks/<br/>create, edit, move, delete"]
    APP --> TPL["templates/<br/>Jinja + Tailwind"]
```

## Move a task (request flow)

```mermaid
sequenceDiagram
    actor U as Member
    participant J as board.js
    participant R as tasks/routes.py
    participant D as Database
    U->>J: Drag card to new column
    J->>R: POST /tasks/id/move {status} + CSRF header
    R->>R: Logged in? Group member? Assignee, creator or leader?
    alt allowed
        R->>D: Update status and add activity log row
        R-->>J: 200 ok
        J-->>U: Reload board
    else not allowed
        R-->>J: 403 error message
        J-->>U: Alert shown
    end
```

## Data model

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

## Database selection (automatic)

```mermaid
flowchart TD
    A["App starts"] --> B{"DATABASE_URL set?"}
    B -->|No| C["SQLite file app.db"]
    B -->|Yes| D{"Neon reachable within 5 s?"}
    D -->|Yes| E["Use Neon PostgreSQL"]
    D -->|No| F["SQLite backup + red warning banner"]
```

## Deployment pipeline

```mermaid
flowchart LR
    DEV["VS Code<br/>local SQLite"] -->|"git push"| GH["GitHub"]
    GH -->|"auto deploy"| V["Vercel<br/>Flask function + CDN"]
    V --> NEON[("Neon PostgreSQL")]
```

## Roles and permissions

```mermaid
flowchart LR
    L["Leader"] --> A1["View board and activity"]
    L --> A2["Create, assign, edit, move, delete any task"]
    M["Member"] --> A1
    M --> A3["Create task for self"]
    M --> A4["Edit or move own tasks"]
    X["Non-member"] --> A5["403 Forbidden"]
```

## Email notifications (optional, free)

```mermaid
flowchart LR
    A["Task assigned or sent for review"] --> F["Flask mailer.py"]
    C["Vercel Cron daily 07:00 UTC"] -->|"Bearer CRON_SECRET"| R["/cron/reminders"]
    R --> F
    F -->|"HTTPS POST + shared secret"| G["Google Apps Script web app"]
    G -->|"MailApp.sendEmail"| E["Student or leader inbox"]
```

Setup: paste `docs/apps-script/Code.gs` into a new project at script.google.com, add the script property `SHARED_SECRET`, deploy as a Web app (Execute as: Me, Access: Anyone), then put the `/exec` URL and the same secret in your environment variables. Email is skipped when they are empty.

## Environment variables and secrets
Never commit keys. Locally copy `.env.example` to `.env` (git-ignored). On Vercel use Project Settings, Environment Variables.

| Name | Purpose |
|---|---|
| `APP_NAME` | Name shown in the app and landing page (default GroupFlow) |
| `SECRET_KEY` | Signs login sessions |
| `DATABASE_URL` | Neon connection string (empty locally = SQLite) |
| `APPS_SCRIPT_URL` | Apps Script Web app URL |
| `APPS_SCRIPT_SECRET` | Must equal the script's `SHARED_SECRET` |
| `CRON_SECRET` | Protects `/cron/reminders` |

## Super admin
Created only from the command line, never from the website, so nobody can promote themselves: `python create_admin.py`. Log in, then open `/admin`.
- Overview: users, groups, tasks, usage meters (users, emails today, database size), recent activity
- Users: search, suspend or reactivate, reset a password
- Groups: view any board read-only, delete a group
- Limits and email: registration on/off, max users, groups per user, members per group, tasks per group, daily write requests per user, daily emails, database storage cap, and a test-email button

Limits are enforced on the server. A cap of 0 means unlimited. Older databases are upgraded automatically on start.

## Run locally (Windows, Command Prompt, inside this folder)
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python seed.py          (optional demo data; login DEMO1 / Password123)
python run.py
```
Open http://127.0.0.1:5000. Run the tests with `python -m pytest -q`.

## Deploy on Vercel
1. Push to GitHub.
2. Create a free Postgres database at neon.tech and copy its connection string.
3. vercel.com, Add New, Project, import the repo.
4. Add environment variables `SECRET_KEY` (long random text) and `DATABASE_URL` (the connection string).
5. Deploy. Tables are created on the first request.

## Git rules
No commits to `main`. Work on a branch (`git checkout -b feature-name`), `git pull` first, small commits, open a pull request. `app.db` is ignored; each person creates their own.

## UI notes
Styling uses the Tailwind Play CDN (loaded in `app/templates/base.html`), so there is no build step. The page needs internet to load Tailwind. For heavy production use, compile CSS with the Tailwind CLI instead.
