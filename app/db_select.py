"""Select the database used by the application.

Local/test runs may fall back to SQLite for convenience. Production/Vercel never
falls back to temporary SQLite because that would make user data disappear when
Vercel creates a new function instance.
"""
from sqlalchemy import create_engine, text


def pick_database(app):
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    database_url = app.config.get("DATABASE_URL", "").strip()
    production = bool(app.config.get("DB_REQUIRED"))

    if production and not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured. Add your hosted PostgreSQL "
            "connection string in Vercel Project Settings > Environment Variables "
            "and redeploy."
        )

    if uri.startswith("sqlite"):
        if production:
            raise RuntimeError(
                "Production database is configured as SQLite. Set DATABASE_URL "
                "to a hosted PostgreSQL connection string and redeploy."
            )
        return

    try:
        # Free hosted Postgres databases can sleep when idle, so allow a few
        # seconds for the database to wake up during the deployment/runtime check.
        engine = create_engine(uri, connect_args={"connect_timeout": 8})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
    except Exception as exc:
        reason = type(exc).__name__
        if production:
            # Never hide a production database outage by switching to /tmp.
            app.logger.error(
                "Production database connection failed (%s). "
                "The application will not use temporary SQLite.",
                reason,
            )
            raise RuntimeError(
                "Production PostgreSQL database is unreachable. Check DATABASE_URL, "
                "the database status/network access, then redeploy."
            ) from exc

        app.logger.warning("Main database unreachable (%s); using local SQLite.", reason)
        app.config["SQLALCHEMY_DATABASE_URI"] = app.config["FALLBACK_DB_URI"]
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}
        app.config["DB_FALLBACK"] = True
        app.config["DB_FALLBACK_REASON"] = reason
