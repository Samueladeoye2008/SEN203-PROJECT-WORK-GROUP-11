"""Pick the database at startup: remote (Neon) if reachable, else SQLite backup."""
from sqlalchemy import create_engine, text


def pick_database(app):
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if uri.startswith("sqlite"):
        return
    try:
        engine = create_engine(uri, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
    except Exception as exc:                    # any failure -> backup DB
        app.logger.warning("Main database unreachable (%s); using backup SQLite.",
                           type(exc).__name__)
        app.config["SQLALCHEMY_DATABASE_URI"] = app.config["FALLBACK_DB_URI"]
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}
        app.config["DB_FALLBACK"] = True
