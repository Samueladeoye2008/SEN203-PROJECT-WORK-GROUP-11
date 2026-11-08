"""Central configuration. Override with environment variables."""
import os

try:                                   # load .env for local runs (optional)
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


IS_VERCEL = bool(os.environ.get("VERCEL"))          # set automatically by Vercel
LOCAL_SQLITE = "sqlite:///" + os.path.join(BASE_DIR, "app.db")
# On Vercel only /tmp is writable (temporary), so the backup DB is demo-only there.
BACKUP_SQLITE = "sqlite:////tmp/app.db" if IS_VERCEL else LOCAL_SQLITE


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me")
    # DATABASE_URL set (Neon/Postgres)  -> use it.
    # Not set, running locally          -> SQLite file (app.db).
    # Not set, on Vercel                -> temporary SQLite in /tmp (demo only).
    _db = os.environ.get("DATABASE_URL") or BACKUP_SQLITE
    if _db.startswith("postgres://"):          # SQLAlchemy needs postgresql://
        _db = _db.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _db
    FALLBACK_DB_URI = BACKUP_SQLITE            # used if the main DB is unreachable
    DB_FALLBACK = False                        # True when fallback is active
    DB_FALLBACK_REASON = ""                    # exception class name, shown to admins only
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Set per survey result (student Q7 / lecturer Q5): who may create tasks.
    ANY_MEMBER_CAN_CREATE = True
    APP_NAME = os.environ.get("APP_NAME", "GroupFlow")
    # Email via Google Apps Script web app (empty = email disabled).
    APPS_SCRIPT_URL = os.environ.get("APPS_SCRIPT_URL", "")
    APPS_SCRIPT_SECRET = os.environ.get("APPS_SCRIPT_SECRET", "")
    CRON_SECRET = os.environ.get("CRON_SECRET", "")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test"
