"""Shows which database the app really uses and what is in it."""
from sqlalchemy import inspect
from app import create_app
from app.extensions import db
from app.models import User

app = create_app()
with app.app_context():
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    # Print only the dialect and safe host/database portion; never expose credentials.
    safe_uri = uri.split("@", 1)[-1] if "@" in uri else uri
    print("Database:", db.engine.dialect.name, "|", safe_uri)
    print("Fallback active:", app.config["DB_FALLBACK"])
    insp = inspect(db.engine)
    tables = sorted(insp.get_table_names())
    print("Tables:", tables)
    expected = {"user", "group", "membership", "task", "activity_log", "setting", "usage_counter"}
    print("Missing tables:", sorted(expected - set(tables)) or "none")
    print("user columns:", [c["name"] for c in insp.get_columns("user")])
    print("Users:", User.query.count(), "| super admins:", User.query.filter_by(is_superadmin=True).count())
