"""Pick the database at startup: remote (Neon) if reachable, else SQLite backup."""
from sqlalchemy import create_engine, text


def pick_database(app):
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if uri.startswith("sqlite"):
        return
    try:
        # Free Neon databases sleep when idle, so allow a few seconds to wake up.
        engine = create_engine(uri, connect_args={"connect_timeout": 8})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
    except Exception as exc:                    # any failure -> backup DB
        reason = type(exc).__name__             # class name only: never log the URL or password
        app.logger.warning("Main database unreachable (%s); using backup SQLite.", reason)
        app.config["SQLALCHEMY_DATABASE_URI"] = app.config["FALLBACK_DB_URI"]
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}
        app.config["DB_FALLBACK"] = True
        app.config["DB_FALLBACK_REASON"] = reason
