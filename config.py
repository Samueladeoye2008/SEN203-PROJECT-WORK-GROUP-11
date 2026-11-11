"""Central configuration. Override with environment variables."""
import os

try:                                   # load .env for local runs (optional)
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

IS_VERCEL = bool(os.environ.get("VERCEL"))
IS_PRODUCTION = IS_VERCEL or os.environ.get("FLASK_ENV", "").lower() == "production"
LOCAL_SQLITE = "sqlite:///" + os.path.join(BASE_DIR, "app.db")
# SQLite is valid for local development only. Vercel's /tmp filesystem is temporary.
BACKUP_SQLITE = "sqlite:////tmp/app.db" if IS_VERCEL else LOCAL_SQLITE


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me")
    DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

    # Production/Vercel MUST use an external PostgreSQL database. We intentionally
    # keep the local SQLite default for development, but never silently switch a
    # deployed app to /tmp when PostgreSQL is missing or unreachable.
    _db = DATABASE_URL or LOCAL_SQLITE
    # SQLAlchemy 2.1 changed the implicit PostgreSQL driver from psycopg2 to
    # psycopg (v3). This project intentionally ships psycopg2-binary, so make
    # the driver explicit. This prevents Vercel from trying to import the
    # uninstalled ``psycopg`` package when DATABASE_URL is a normal
    # postgresql:// URL.
    if _db.startswith("postgres://"):
        _db = _db.replace("postgres://", "postgresql://", 1)
    if _db.startswith("postgresql://"):
        _db = _db.replace("postgresql://", "postgresql+psycopg2://", 1)
    SQLALCHEMY_DATABASE_URI = _db
    FALLBACK_DB_URI = BACKUP_SQLITE            # local/test fallback only
    DB_REQUIRED = IS_PRODUCTION
    DB_FALLBACK = False                        # True only for local/test fallback
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
    # Vercel terminates HTTPS before the Flask function, so cookies must work
    # correctly across that proxy boundary.
    SESSION_COOKIE_SECURE = IS_PRODUCTION


class TestConfig(Config):
    TESTING = True
    DB_REQUIRED = False
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test"
